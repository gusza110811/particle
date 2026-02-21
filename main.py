import particle
from vector import Vector2d
import pygame

class Simulation:
    def __init__(self, screen:pygame.Surface):
        self.screen = screen
        self.running = True
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)

        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        self.particles:list[particle.Particle] = []

        self.debug = True

    def main(self):

        test = particle.Particle()

        self.particles.append(test)

        test.vel.translate((10,0))

        while self.running:
            self.event()
            self.physic()

            self.render()

            self.clock.tick(30)

    
    def render(self):
        screen = self.screen

        screen.fill(pygame.Color(0,0,0))

        for particle in self.particles:
            pos = particle.pos + self.centerPos + self.cam
            pygame.draw.circle(screen,pygame.Color(255,255,255),pos.tuple(),particle.radius)
        
        if self.debug:
            self.dbgOverlay()

        pygame.display.update()
    
    def physic(self):
        for particle in self.particles:
            particle.onPhysic()

    def event(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
    
    def dbgOverlay(self):
        font = self.dbgfont
        screen = self.screen
        items = [
            f"fps: {self.clock.get_fps()}",
            f"objects: {len(self.particles)}"
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