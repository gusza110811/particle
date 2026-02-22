import particle as Particle
from vector import Vector2d
import pygame
import random
import math

class Simulation:
    def __init__(self, screen:pygame.Surface):
        self.screen = screen
        self.running = True
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)

        self.horizontalLim = 500
        self.verticalLim = 500
        self.screenHorLim = screen.get_width()
        self.screenVerLim = screen.get_height()
        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        # camZoom is the power of 2 to scale the world by when rendering, so camZoom of 1 means 2x zoom, camZoom of -1 means 0.5x zoom
        self.camZoom = math.log2((self.screenVerLim/2)/self.verticalLim)
        #self.camZoom = 0

        self.borderTopLeft = Vector2d(self.horizontalLim*-1,self.verticalLim*-1)
        self.borderBottomRight = Vector2d(self.horizontalLim,self.verticalLim)

        self.gravityRate = Vector2d(0,1)
        self.radius = 4
        self.velConserve = 1
        self.elasticity = 1

        self.particles:list[Particle.Particle] = []
        self.cell_size = self.radius*2

        self.paused = False

        self.debug = True

        self.borderType = 1 # 0 for circle, 1 for square

    def main(self):

        self.buffer = []

        for idx in range(300):
            for idk in range(1,5):
                part = Particle.Particle((0,-self.verticalLim+idk*self.radius*1.5))
                part.vel.x -= 10
                self.buffer.append(part)
        
        clock = self.clock

        while self.running:
            self.frame(clock.get_time()/1000)
            clock.tick()
    
    def frame(self,dt):
        buffer = self.buffer

        self.event(dt)
        if not self.paused:
            if buffer:
                self.particles.append(buffer.pop())
                self.particles.append(buffer.pop())
                self.particles.append(buffer.pop())
                self.particles.append(buffer.pop())
            self.physic()

        self.render()

    
    def render(self):
        screen = self.screen

        screen.fill(pygame.Color(0,0,0))
        radius = self.radius

        centerPos = self.centerPos
        horLim = self.screenHorLim
        verLim = self.screenVerLim
        r = max(radius * 2**self.camZoom,1)
        d = r*2
        circle_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, pygame.Color(255,255,255), (r, r), r)

        for particle in self.particles:
            pos = (particle.pos - self.cam).scale(2**self.camZoom).translate(centerPos)
            # culling
            if (abs(pos.x) > horLim+d) or (abs(pos.y) > verLim+d):
                continue

            screen.blit(circle_surf, (pos.x-r, pos.y-r))
        
        if self.debug:
            self.dbgOverlay()

        pygame.display.update()
    
    def physic(self):
        gravity = self.gravityRate
        radius = self.radius
        velConserve = self.velConserve
        elasticity = self.elasticity
        particles = self.particles
        cs = self.cell_size
        rs = radius*2

        substep = 16
        substepsize = 1/substep
        max_vel = radius*substep

        for _ in range(substep):
            self.doGravity(gravity,substepsize)
            self.boundCheck(elasticity,substepsize)
            self.overlapCheck(particles,cs,elasticity,rs)
            self.doPhysicMethod(max_vel,velConserve,substepsize)
    def buildGrid(self, particles, cs):
        grid = {}

        for p in particles:
            cx = int(p.pos.x // cs)
            cy = int(p.pos.y // cs)

            key = (cx, cy)
            if key in grid:
                grid[key].append(p)
            else:
                grid[key] = [p]

        return grid
    
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
    
    def overlapCheck(self, particles, cs, elasticity, rs):
        applyOverlap = self.applyOverlap
        grid:dict[tuple[int,int],list[Particle.Particle]] = self.buildGrid(particles,cs)

        for (cx, cy), cell_particles in grid.items():

            for id1 in range(len(cell_particles)):
                p1 = cell_particles[id1]
                p1x = p1.pos.x
                p1y = p1.pos.y
                # Check this cell and neighbors
                for ox in (-1,0,1):
                    for oy in (-1,0,1):
                        neighbor_key = (cx + ox, cy + oy)

                        neighbor_particles = grid.get(neighbor_key)

                        if not neighbor_particles:
                            continue

                        for p2 in neighbor_particles:

                            dx = p2.pos.x - p1x
                            dy = p2.pos.y - p1y
                            dist_sq = dx*dx + dy*dy

                            if dist_sq < rs*rs:
                                applyOverlap(p1, p2, dx, dy, dist_sq, rs, elasticity)
            #grid[(cx, cy)] = None
    
    def boundCheck(self, elasticity, substepsize):
        if self.borderType == 0:
            self.circleBound(elasticity, substepsize)
        elif self.borderType == 1:
            self.squareBound(elasticity, substepsize)
    
    def circleBound(self, elasticity, substepsize):
        particles = self.particles
        # circle boundary
        radius = self.verticalLim
        for id in range(len(particles)):
            particle = particles[id]
            dist = math.sqrt(particle.pos.x*particle.pos.x + particle.pos.y*particle.pos.y)

            if radius < dist:
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
                particles[id].vel.x = abs(particles[id].vel.x) * elasticity * substepsize
                particles[id].pos.x = self.borderTopLeft.x
            elif particles[id].pos.x > self.borderBottomRight.x:
                particles[id].vel.x = -abs(particles[id].vel.x) * elasticity * substepsize
                particles[id].pos.x = self.borderBottomRight.x
            elif particles[id].pos.y < self.borderTopLeft.y:
                particles[id].vel.y = abs(particles[id].vel.y) * elasticity * substepsize
                particles[id].pos.y = self.borderTopLeft.y
            elif particles[id].pos.y > self.borderBottomRight.y:
                particles[id].vel.y = -abs(particles[id].vel.y) * elasticity * substepsize
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
        try:
            normalx = dx/dist
        except ZeroDivisionError:
            normalx = 0
        try:
            normaly = dy/dist
        except ZeroDivisionError:
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

    def event(self,dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_f:
                    self.paused = True
                    self.physic()
            elif event.type == pygame.MOUSEWHEEL:
                self.camZoom += event.y/10
        if pygame.mouse.get_pressed()[0]:
            self.particles.append(Particle.Particle(
                    Vector2d(pygame.mouse.get_pos()).translate(-self.centerPos).scale(1/2**self.camZoom).translate(self.cam).translate((random.random(),random.random()))
            ))
        if pygame.mouse.get_pressed()[2]:
            mouse_pos = Vector2d(pygame.mouse.get_pos()).translate(-self.centerPos).scale(1/2**self.camZoom).translate(self.cam)
            closest = None
            closestdist = math.inf
            for idx, part in enumerate(self.particles):
                dist = (part.pos-mouse_pos).magnitude()
                if dist < closestdist:
                    closest = idx
                    closestdist = dist
            
            if closestdist < self.radius:
                self.particles.pop(closest)
        
        pressed = pygame.key.get_pressed()
        dir = Vector2d()
        if pressed[pygame.K_w]:
            dir.translate((0,-1))
        if pressed[pygame.K_s]:
            dir.translate((0,1))
        if pressed[pygame.K_a]:
            dir.translate((-1,0))
        if pressed[pygame.K_d]:
            dir.translate((1,0))
        
        self.cam.translate(dir.scale(300*(2**-self.camZoom)*dt))

    def dbgOverlay(self):
        font = self.dbgfont
        screen = self.screen
        items = [
            f"fps: {self.clock.get_fps()}",
            f"objects: {len(self.particles)}",
            "paused" if self.paused else "unpaused",
            f"zoom: {2**self.camZoom:.2f}x",
        ]

        for idx, item in enumerate(items):
            text = font.render(item,True,pygame.Color(0,255,0))
            screen.blit(text,(0,idx*20))


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((960,720))

    sim = Simulation(screen)

    sim.main()