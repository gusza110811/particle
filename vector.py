from __future__ import annotations
import math

class Vector2d:
    def __init__(self,x:float|tuple|Vector2d=0,y:float=None):
        if isinstance(x,Vector2d):
            x, y = x.x, x.y

        elif isinstance(x,tuple):
            x, y, *other = x
            if other:
                raise ValueError("Too many arguments")
        self.x = float(x)
        if y:
            self.y = float(y)
        else:
            self.y = float(x)
    
    def __add__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot add Vector2d to {type(vector).__name__}")
        
        return Vector2d(self.x+vector.x,self.y+vector.y)
    def __pos__(self):
        return self.clone()
    __radd__ = __add__
    def __sub__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot subtract Vector2d from {type(vector).__name__}")
        
        return Vector2d(self.x-vector.x,self.y-vector.y)
    def __rsub__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot subtract Vector2d from {type(vector).__name__}")
        return Vector2d(vector.x-self.x,vector.y-self.y)
    def __neg__(self):

        return Vector2d(0-self.x,0-self.y)
    def __mul__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot multiply Vector2d by {type(vector).__name__}")
        
        return Vector2d(self.x*vector.x,self.y*vector.y)
    __rmul__ = __mul__
    def __truediv__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot divide Vector2d by {type(vector).__name__}")
        
        return Vector2d(self.x/vector.x,self.y/vector.y)
    def __rtruediv__(self,vector:Vector2d|tuple):
        if not isinstance(vector,Vector2d):
            try:
                vector = Vector2d(vector)
            except TypeError:
                raise ValueError(f"Cannot divide Vector2d by {type(vector).__name__}")
        
        return Vector2d(vector.x/self.x,vector.y/self.y)

    def translate(self,translation:Vector2d|tuple):
        if not isinstance(translation,Vector2d):
            try:
                translation = Vector2d(translation)
            except TypeError:
                raise ValueError(f"Cannot translate Vector2d by {type(translation).__name__}")
        self.x += translation.x
        self.y += translation.y

        return self
    def scale(self,scale:float|int):
        self.x *= scale
        self.y *= scale

        return self
    
    def __eq__(self,obj):
        if not isinstance(obj,Vector2d):
            return False
        if obj is self:
            return True
        if self.x == obj.x and self.y == obj.y:
            return True
        return False
    
    def magnitude(self):
        return math.hypot(self.x,self.y)
    
    def normalize(self):
        magnitude = self.magnitude()
        if magnitude > 0:
            nx = self.x/magnitude
        else:
            nx = 0
        if magnitude > 0:
            ny = self.y/magnitude
        else:
            ny = 0
    
        return Vector2d(nx, ny)

    def clone(self):
        return Vector2d(self.x,self.y)
    def tuple(self):
        return (self.x,self.y)
    
    def __repr__(self):
        return f"Vector({self.x}, {self.y})"