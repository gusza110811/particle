from vector import Vector2d

class Particle:
    def __init__(self, pos:Vector2d=Vector2d(0)):
        self.radius = 10
        self.pos = pos
        self.vel = Vector2d()
        self.velConserve = 0.9
    
    def onPhysic(self):
        self.pos.translate(self.vel)
        self.vel.scale(self.velConserve)