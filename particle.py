from vector import Vector2d

class Particle:
    def __init__(self, pos:Vector2d|tuple=Vector2d(0)):
        self.pos = Vector2d(pos)
        self.vel = Vector2d()
    
    def __repr__(self):
        return f"({self.pos} {self.vel})"
