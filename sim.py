import struct
import sys
import particle as Particle
from vector import Vector2d
import math
import argparse
import time
import io
import threading
import json

class Emitter:
    def __init__(self, pos:Vector2d, area:Vector2d, startVel:Vector2d, timeToLive:int, timeToStart:int):
        self.pos = pos
        self.area = area
        self.startVel = startVel
        self.timeToLive = timeToLive
        self.timeToStart = timeToStart

class Simulation:
    def __init__(self):
        self.running = True

        self.horizontalLim = 512
        self.verticalLim = 512

        self.borderTopLeft = Vector2d(self.horizontalLim*-1,self.verticalLim*-1)
        self.borderBottomRight = Vector2d(self.horizontalLim,self.verticalLim)

        self.gravityRate = Vector2d(0,0.2)
        self.radius = 4
        self.velConserve = 1
        self.elasticity = 0.95

        self.emitters:list[Emitter] = []
        self.particles:list[Particle.Particle] = []
        self.cell_size = self.radius*2
        self.substep = 8
        self.velLimit = 32

        self.output:io.FileIO = None

        self.debug = True
        self.writeFrame = True

        self.borderType = 1 # 0 for circle, 1 for square
    
    def addEmitter(self, emitter:Emitter):
        self.emitters.append(emitter)

    def addEmitters(self, emitters:list[Emitter]):
        self.emitters.extend(emitters)

    def main(self):
        # write header for simulation file output
        self.output.write(b"\xFFPARTSIM")
        self.output.write((1).to_bytes(1,'little'))
        self.output.write(self.horizontalLim.to_bytes(4,'little'))
        self.output.write(self.verticalLim.to_bytes(4,'little'))
        self.output.write(bytearray(struct.pack("<f",self.radius)))
        self.output.write(self.borderType.to_bytes(1,'little'))

        writeFrame = self.writeFrame
        timestart = time.time()
        while self.running:
            timeb = time.perf_counter()
            self.Emit()
            self.physic()
            if self.frame >= self.targetFrames and self.targetFrames > 0: # negative frame count means indefinite
                self.running = False
            timetaken = time.perf_counter() - timeb
            print(f"frame {self.frame}" + ("/" + str(self.targetFrames) if self.targetFrames > 0 else "") + f"{timetaken*1000:4.0f}ms  ",end="\r",file=sys.stderr)
            self.saveFrame(writeFrame)
        print(f"\ntook {time.time()-timestart:.4f} seconds",file=sys.stderr)
        if not writeFrame:
            writing = True
            def blink():
                while writing:
                    print("\b.",end="",flush=True)
                    time.sleep(0.1)
                    print("\b ",end="",flush=True)
                    time.sleep(0.1)
            print("writing ",end="")
            blinkthread = threading.Thread(target=blink,daemon=True)
            blinkthread.start()
            self.output.write(self.buffer)
            writing = False
            print("\ndone")
    
    def initHeadless(self,output,targetFrames):
        self.buffer = bytearray()
        self.output = output
        self.frame = 0
        self.targetFrames = targetFrames
    
    def saveFrame(self,write:bool):
        particles = self.particles
        # output format: [frame id u32] [particle count u32]
        # [particle x f32] [particle y f32]
        if write:
            buffer = bytearray()
        else:
            buffer = self.buffer
        buffer.extend(self.frame.to_bytes(4,'little'))
        buffer.extend(len(particles).to_bytes(4,'little'))
        for part in particles:
            buffer.extend(bytearray(struct.pack("f",part.pos.x)))
            buffer.extend(bytearray(struct.pack("f",part.pos.y)))
        if write:
            try:
                self.output.write(buffer)
            except BrokenPipeError:
                self.running = False
                print("\nOutput pipe closed, stopping simulation", file=sys.stderr)
        self.frame += 1
    
    def Emit(self):
        emitters = self.emitters
        particles = self.particles
        diameter = self.radius*2
        for idx, emitter in enumerate(emitters):
            if emitter.timeToStart <= 0:
                for x in range(int(emitter.area.x)):
                    for y in range(int(emitter.area.y)):
                        pos = Vector2d(
                            emitter.pos.x+x*diameter,
                            emitter.pos.y+y*diameter
                        )
                        vel = Vector2d(
                            emitter.startVel.x,
                            emitter.startVel.y
                        )
                        particles.append(Particle.Particle(pos,vel))
                emitter.timeToLive -= 1
                if emitter.timeToLive <= 0:
                    emitters[idx] = None
            else:
                emitter.timeToStart -= 1
        
        self.emitters = [e for e in emitters if e is not None]

    def physic(self):
        gravity = self.gravityRate
        radius = self.radius
        velConserve = self.velConserve
        elasticity = self.elasticity
        particles = self.particles
        cs = self.cell_size
        rs = radius*2
        rssq = rs*rs

        substep = self.substep
        substepsize = 1/substep
        max_vel = self.velLimit

        grid, sx, sy = self.buildGrid(particles,cs)

        for _ in range(substep):
            self.doGravity(gravity,substepsize)
            self.boundCheck(elasticity,substepsize)
            self.overlapCheck(grid,sx,sy,elasticity,rs,rssq)
            self.doPhysicMethod(max_vel,velConserve,substepsize)
    def buildGrid(self, particles, cs):
        sizex = self.horizontalLim//self.radius
        sizey = self.verticalLim//self.radius
        grid = [[[] for _ in range(sizex)] for _ in range(sizey)]

        for p in particles:
            cx = int(p.pos.x // cs)
            cy = int(p.pos.y // cs)
            if cx >= sizex or cy >= sizey:
                continue

            grid[cx][cy].append(p)

        return grid, sizex, sizey
    
    def doPhysicMethod(self,max_vel,velConserve,subStepSize):
        particles = self.particles
        applyPhysic = self.applyPhysic
        for id in range(len(particles)):
            applyPhysic(particles[id],max_vel,velConserve,subStepSize)

    def doGravity(self,gravityr,substepsize):
        particles = self.particles
        gravity = self.gravity
        gravityrs = gravityr*substepsize
        for id in range(len(particles)):
            gravity(particles[id],gravityrs)
    
    def gravity(self,part,gravity):
        part.vel.translate(gravity)
    
    def overlapCheck(self, grid, sx, sy, elasticity, rs, rssq):
        applyOverlap = self.applyOverlap

        for cx, row in enumerate(grid):
            for cy, cell_particles in enumerate(row):
                for p1 in cell_particles:
                    p1x = p1.pos.x
                    p1y = p1.pos.y
                    # Check this cell and neighbors
                    for ox in (-1,0,1):
                        for oy in (-1,0,1):
                            x = cx+ox
                            y = cy+oy

                            if x >= sx or y >= sy:
                                continue

                            neighbor_particles = grid[x][y]

                            if not neighbor_particles:
                                continue

                            for p2 in neighbor_particles:

                                p2pos = p2.pos

                                dx = p2pos.x - p1x
                                dy = p2pos.y - p1y
                                dist_sq = dx*dx + dy*dy

                                if dist_sq < rssq:
                                    applyOverlap(p1, p2, dx, dy, dist_sq, rs, elasticity)
    
    def boundCheck(self, elasticity, substepsize):
        if self.borderType == 0:
            self.circleBound(elasticity, substepsize)
        elif self.borderType == 1:
            self.squareBound(elasticity, substepsize)
    
    def circleBound(self, elasticity, substepsize):
        particles = self.particles
        # circle boundary
        radius = self.verticalLim
        radiussq = radius*radius
        for id in range(len(particles)):
            particle = particles[id]
            distsq = particle.pos.x*particle.pos.x + particle.pos.y*particle.pos.y

            if radiussq < distsq:
                dist = math.sqrt(distsq)
                correctionx = particle.pos.x / dist * (radius - dist)
                correctiony = particle.pos.y / dist * (radius - dist)
                correctionx *= substepsize
                correctiony *= substepsize
                #print(dist,radius,correction)
                particle.pos.x += correctionx
                particle.pos.y += correctiony
                particle.vel.x *= elasticity
                particle.vel.y *= elasticity
                particle.vel.x += correctionx
                particle.vel.y += correctiony
    
    def squareBound(self, elasticity, substepsize):
        particles = self.particles
        # square boundary
        for id in range(len(particles)):
            if particles[id].pos.x < self.borderTopLeft.x:
                particles[id].vel.x = abs(particles[id].vel.x) * elasticity
                particles[id].pos.x = self.borderTopLeft.x
            elif particles[id].pos.x > self.borderBottomRight.x:
                particles[id].vel.x = -abs(particles[id].vel.x) * elasticity
                particles[id].pos.x = self.borderBottomRight.x
            if particles[id].pos.y < self.borderTopLeft.y:
                particles[id].vel.y = abs(particles[id].vel.y) * elasticity
                particles[id].pos.y = self.borderTopLeft.y
            elif particles[id].pos.y > self.borderBottomRight.y:
                particles[id].vel.y = -abs(particles[id].vel.y) * elasticity
                particles[id].pos.y = self.borderBottomRight.y
    # assume all particle have equal mass
    def applyCollide(self,pri:Particle.Particle,other:Particle.Particle,
                     nx,ny,elasticity):

        # relative velocity
        rvx = pri.vel.x - other.vel.x
        rvy = pri.vel.y - other.vel.y

        vel_along_normal = rvx * nx + rvy * ny

        if vel_along_normal < 0:
            return  # moving apart

        impulse = vel_along_normal * elasticity

        imx = impulse * nx
        imy = impulse *ny

        pri.vel.x -= imx
        pri.vel.y -= imy
        other.vel.x += imx
        other.vel.y += imy
    def applyOverlap(self,pri:Particle.Particle,other:Particle.Particle,
                     dx, dy, dist_sq, rs, elasticity):
        dist = math.sqrt(dist_sq)
        if dist > 0:
            normalx = dx/dist
            normaly = dy/dist
        else:
            normalx = 0
            normaly = 0
        self.applyCollide(pri,other,normalx,normaly,elasticity)
        expectdist = rs-dist

        correctionx = normalx*expectdist/2
        correctiony = normaly*expectdist/2

        pri.pos.x -= correctionx
        pri.pos.y -= correctiony

        other.pos.x += correctionx
        other.pos.y += correctiony

    def applyPhysic(self,part:Particle.Particle,max_vel,velConserve,subStepSize):
        vel = part.vel
        pos = part.pos

        # cap velocity to reduce tunneling
        if vel.x*vel.x + vel.y*vel.y > max_vel*max_vel:
            vel = vel.normalize().scale(max_vel)

        pos.x += vel.x * subStepSize
        pos.y += vel.y * subStepSize
        lossx = (1-velConserve) * vel.x * subStepSize
        lossy = (1-velConserve) * vel.y * subStepSize
        vel.x -= lossx
        vel.y -= lossy

def test():
    sim = Simulation()
    with open("output.sim","wb") as f:
        sim.initHeadless(f,1000)
        sim.main()

def loadConfig(sim:Simulation,filename:str="simcfg.json"):
    with open(filename,"r") as f:
        data:dict = json.load(f)

    simSize = data.get("simSize", [None, None])
    if simSize[0] is not None and simSize[1] is not None:
        sim.horizontalLim = simSize[0]
        sim.verticalLim = simSize[1]
    else:
        print("No simulation size (SimSize) specified, using default 512x512", file=sys.stderr)
    
    gravity = data.get("gravity", None)
    if gravity is not None:
        sim.gravityRate = Vector2d(gravity[0], gravity[1])
    else:
        print("No gravity specified, using default (0,0.2)", file=sys.stderr)

    radius = data.get("radius", None)
    if radius is not None:
        sim.radius = radius
    else:
        print("No particle radius specified, using default 4", file=sys.stderr)
    
    dampening = data.get("dampening", None)
    if dampening is not None:
        sim.velConserve = 1 - dampening
    else:
        print("No dampening specified, using default 0 (no dampening)", file=sys.stderr)
    
    elasticity = data.get("elasticity", None)
    if elasticity is not None:
        sim.elasticity = elasticity
    else:
        print("No elasticity specified, using default 0.95", file=sys.stderr)
    
    substep = data.get("substep", None)
    if substep is not None:
        sim.substep = substep
    else:
        print("No substep count (substep) specified, using default 8", file=sys.stderr)
    
    velLimit = data.get("velLimit", None)
    if substep is not None:
        sim.velLimit = velLimit
    else:
        print("No velocity limit (velLimit) specified, using default 32", file=sys.stderr)

    emitters = []
    emitterList = data.get("emitters", [])
    if emitterList:
        for item in emitterList:
            pos = Vector2d(item["pos"][0],item["pos"][1])
            area = Vector2d(item["area"][0],item["area"][1])
            startVel = Vector2d(item["startVel"][0],item["startVel"][1])
            timeToLive = item["timeToLive"]
            timeToStart = item["timeToStart"]
            emitters.append(Emitter(pos,area,startVel,timeToLive,timeToStart))
        sim.addEmitters(emitters)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Run particle simulation")
    argparser.add_argument("--output", "-o", type=str, default="output.sim", help="Output file for simulation data", nargs="?")
    argparser.add_argument("--frames", "-f", type=int, default=1000, help="Number of frames to simulate")
    argparser.add_argument("--no-write", action="store_false", dest="writeFrame", help="Don't write frames during simulation, write at the end (faster but more memory usage)")
    argparser.add_argument("--config", "-c", type=str, default="simcfg.json", help="Configuration file for simulation parameters", nargs="?")
    args = argparser.parse_args()

    output_file = args.output
    if output_file == "-":
        output_file = sys.stdout.buffer
    else:
        output_file = open(output_file, "wb")
    
    if args.frames < 0 and output_file != sys.stdout.buffer:
        print("Warning: negative frame count means indefinite simulation, but output is not stdout, this may result in a very large file", file=sys.stderr)

    frames = args.frames
    sim = Simulation()
    sim.initHeadless(output_file,frames)

    loadConfig(sim,args.config)

    sim.writeFrame = args.writeFrame
    sim.main()

    if args.output != "-":
        output_file.close()
    
    sys.stderr.close()