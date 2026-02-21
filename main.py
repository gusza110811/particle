import particle as Particle
from vector import Vector2d
import pygame
import random

class Simulation:
    def __init__(self, screen:pygame.Surface):
        self.screen = screen
        self.running = True
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)

        self.horizontalLim = screen.get_width()
        self.verticalLim = screen.get_height()
        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        self.borderTopLeft = Vector2d(-screen.get_width()//2,-screen.get_height()//2)
        self.borderBottomRight = Vector2d(screen.get_width()//2,screen.get_height()//2)

        self.particles:list[Particle.Particle] = []

        self.debug = True

    def main(self):

        for idx in range(15):
            for idk in range(15):
                self.particles.append(Particle.Particle((idx*40-370 + random.random(),idk*40-270)))

        while self.running:
            self.event()
            self.physic()

            self.render()

            self.clock.tick(30)

    
    def render(self):
        screen = self.screen

        screen.fill(pygame.Color(0,0,0))

        for particle in self.particles:
            pos = (particle.pos + self.centerPos).translate(self.cam)
            # culling
            if (abs(pos.x) > self.horizontalLim+particle.radius) or (abs(pos.y) > self.verticalLim+particle.radius):
                continue

            pygame.draw.circle(screen,pygame.Color(255,255,255),pos.tuple(),particle.radius)
        
        if self.debug:
            self.dbgOverlay()

        pygame.display.update()
    
    def physic(self):
        particles = self.particles
        for particle in particles:

            for other in particles:
                if other is particle: continue
                if (other.pos - particle.pos).magnitude() < (other.radius + particle.radius):
                    particle.onCollide(other)
            
            if particle.pos.x < self.borderTopLeft.x:
                particle.vel.x = abs(particle.vel.x)
            elif particle.pos.x > self.borderBottomRight.x:
                particle.vel.x = -abs(particle.vel.x)
            elif particle.pos.y < self.borderTopLeft.y:
                particle.vel.y = abs(particle.vel.y)
            elif particle.pos.y > self.borderBottomRight.y:
                particle.vel.y = -abs(particle.vel.y)
            
            particle.onPhysic()


    def event(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.particles.append(Particle.Particle(
                        Vector2d(pygame.mouse.get_pos()) - self.cam - self.centerPos
                    ))
    
    def dbgOverlay(self):
        font = self.dbgfont
        screen = self.screen
        items = [
            f"fps: {self.clock.get_fps()}",
            f"objects: {len(self.particles)}",
        ]

        for idx, item in enumerate(items):
            text = font.render(item,True,pygame.Color(0,255,0))
            screen.blit(text,(0,idx*20))


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((800,600))

    sim = Simulation(screen)

    sim.main()