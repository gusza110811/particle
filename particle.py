from vector import Vector2d

class Particle:
    def __init__(self, pos:Vector2d|tuple=Vector2d(0)):
        self.radius = 20
        self.pos = Vector2d(pos)
        self.vel = Vector2d()
        self.velConserve = 0.90
        self.gravity = Vector2d(0,1)
    
    def onPhysic(self):
        self.pos.translate(self.vel)
        self.vel.translate(self.gravity)
        self.vel.scale(self.velConserve)
    
    # assume all particle have equal mass
    def onCollide(self,other:"Particle"):
        dist = (self.pos - other.pos).magnitude()
        nx = (self.pos.x-other.pos.x) / dist
        ny = (self.pos.y-other.pos.y) / dist

        # relative velocity
        rvx = other.vel.x - self.vel.x
        rvy = other.vel.y - self.vel.y

        vel_along_normal = rvx * nx + rvy * ny

        if vel_along_normal < 0:
            return  # moving apart

        impulse = -vel_along_normal

        self.vel.x -= impulse * nx
        self.vel.y -= impulse * ny
        other.vel.x += impulse * nx
        other.vel.y += impulse * ny
    
    def onOverlap(self,other:"Particle"):
        dist = (self.pos - other.pos).magnitude()
        normal = (self.pos - other.pos).normalize()

        pushdenom = 100

        self.vel.translate(normal*dist/pushdenom)
        other.vel.translate(normal*dist/pushdenom*-1)
