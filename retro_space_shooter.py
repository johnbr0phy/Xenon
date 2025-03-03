import pygame
import random
import sys
import math
import numpy as np
import pygame.gfxdraw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

# -------------------------
# Game settings and colors
# -------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GREEN   = (50, 205, 50)       # Lime green for player ship
DARK_GREEN = (0, 100, 0)
RED     = (255, 69, 0)        # OrangeRed for enemy ships
ORANGE  = (255, 165, 0)
YELLOW  = (255, 215, 0)       # Gold for bullets
BLUE    = (30, 144, 255)      # DodgerBlue for enemy cockpit

# -------------------------
# Pygame & OpenGL Setup
# -------------------------
pygame.init()
# Set up pygame display in OPENGL mode.
pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("Space Shooter with Shaders")
clock = pygame.time.Clock()

# Create an offscreen surface for 2D drawing (the “scene”)
scene_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()

# -------------------------
# GLSL Shader Setup
# -------------------------
vertex_shader_source = """
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec2 aTexCoord;
out vec2 TexCoord;
void main(){
    TexCoord = aTexCoord;
    gl_Position = vec4(aPos, 0.0, 1.0);
}
"""

fragment_shader_source = """
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;
uniform sampler2D screenTexture;
uniform float time;
void main(){
    vec2 uv = TexCoord;
    vec4 color = texture(screenTexture, uv);
    // Vignette effect based on distance from center
    float dist = distance(uv, vec2(0.5,0.5));
    color.rgb *= smoothstep(0.8, 0.5, dist);
    // Subtle time-based color shift effect
    color.r += sin(time + uv.x * 10.0) * 0.05;
    FragColor = color;
}
"""

shader = compileProgram(
    compileShader(vertex_shader_source, GL_VERTEX_SHADER),
    compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
)

# Set up a fullscreen quad (two triangles covering [-1,1] in NDC)
quad_vertices = np.array([
    # positions   # texCoords
    -1.0, -1.0,   0.0, 0.0,
     1.0, -1.0,   1.0, 0.0,
     1.0,  1.0,   1.0, 1.0,
    -1.0,  1.0,   0.0, 1.0,
], dtype=np.float32)

quad_indices = np.array([
    0, 1, 2,
    2, 3, 0
], dtype=np.uint32)

# Create VAO, VBO, and EBO for the quad
VAO = glGenVertexArrays(1)
VBO = glGenBuffers(1)
EBO = glGenBuffers(1)

glBindVertexArray(VAO)
glBindBuffer(GL_ARRAY_BUFFER, VBO)
glBufferData(GL_ARRAY_BUFFER, quad_vertices.nbytes, quad_vertices, GL_STATIC_DRAW)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
glBufferData(GL_ELEMENT_ARRAY_BUFFER, quad_indices.nbytes, quad_indices, GL_STATIC_DRAW)
# position attribute (location=0)
glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * quad_vertices.itemsize, ctypes.c_void_p(0))
glEnableVertexAttribArray(0)
# texture coordinate attribute (location=1)
glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * quad_vertices.itemsize, ctypes.c_void_p(2 * quad_vertices.itemsize))
glEnableVertexAttribArray(1)
glBindBuffer(GL_ARRAY_BUFFER, 0)
glBindVertexArray(0)

# Create a texture to hold the scene
scene_texture = glGenTextures(1)
glBindTexture(GL_TEXTURE_2D, scene_texture)
# Allocate empty texture
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SCREEN_WIDTH, SCREEN_HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
# Set texture parameters
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
glBindTexture(GL_TEXTURE_2D, 0)

# -------------------------
# Game Asset Functions
# -------------------------
def create_player_asset():
    size = 40
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    points = [(size // 2, 5), (5, size - 5), (size - 5, size - 5)]
    offset_points = [(x + 2, y + 2) for (x, y) in points]
    pygame.gfxdraw.filled_polygon(surface, offset_points, (0, 0, 0, 100))
    pygame.gfxdraw.filled_polygon(surface, points, GREEN)
    pygame.gfxdraw.aapolygon(surface, points, DARK_GREEN)
    return surface

def create_enemy_asset():
    size = 30
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    points = [(size // 2, 0), (0, size // 2), (size // 2, size), (size, size // 2)]
    pygame.gfxdraw.filled_polygon(surface, points, RED)
    pygame.gfxdraw.aapolygon(surface, points, ORANGE)
    pygame.gfxdraw.filled_circle(surface, size // 2, size // 2, size // 6, BLUE)
    pygame.gfxdraw.aacircle(surface, size // 2, size // 2, size // 6, WHITE)
    return surface

def create_bullet_asset():
    width, height = 6, 12
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    center = (width // 2, height // 2)
    pygame.gfxdraw.filled_circle(surface, center[0], center[1], width // 2, YELLOW)
    pygame.gfxdraw.aacircle(surface, center[0], center[1], width // 2, ORANGE)
    return surface

# -------------------------
# Game Sprite Classes
# -------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = create_player_asset()
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 5
        self.shoot_delay = 250  # ms between shots
        self.last_shot = pygame.time.get_ticks()
    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
    def shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            bullet = Bullet(self.rect.centerx, self.rect.top)
            all_sprites.add(bullet)
            bullets.add(bullet)

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = create_enemy_asset()
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        self.speedy = random.randrange(2, 6)
        self.speedx = random.randrange(-1, 2)
    def update(self):
        self.rect.y += self.speedy
        self.rect.x += self.speedx
        if (self.rect.top > SCREEN_HEIGHT + 10 or
            self.rect.left < -25 or
            self.rect.right > SCREEN_WIDTH + 20):
            self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
            self.rect.y = random.randrange(-100, -40)
            self.speedy = random.randrange(2, 6)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_bullet_asset()
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speedy = -10
    def update(self):
        self.rect.y += self.speedy
        if self.rect.bottom < 0:
            self.kill()

class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, color):
        super().__init__()
        self.duration = 30  # frames
        self.frame_index = 0
        self.max_radius = 30
        self.color = color
        self.image = pygame.Surface((self.max_radius*2, self.max_radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=center)
    def update(self):
        self.frame_index += 1
        if self.frame_index > self.duration:
            self.kill()
        else:
            radius = int((self.frame_index / self.duration) * self.max_radius)
            alpha = max(255 - int((self.frame_index / self.duration) * 255), 0)
            self.image.fill((0,0,0,0))
            if radius > 0:
                temp_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.gfxdraw.filled_circle(temp_surf, radius, radius, radius, (*self.color, alpha))
                self.image.blit(temp_surf, (self.max_radius - radius, self.max_radius - radius))

class Star:
    def __init__(self):
        self.x = random.randrange(0, SCREEN_WIDTH)
        self.y = random.randrange(0, SCREEN_HEIGHT)
        self.size = random.choice([1, 2])
        self.speed = random.uniform(0.5, 2.5)
        brightness = random.randint(100, 255)
        self.color = (brightness, brightness, brightness)
    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randrange(0, SCREEN_WIDTH)
    def draw(self, surface):
        pygame.gfxdraw.pixel(surface, int(self.x), int(self.y), self.color)

# -------------------------
# Sprite Groups and Stars
# -------------------------
all_sprites = pygame.sprite.Group()
enemies    = pygame.sprite.Group()
bullets    = pygame.sprite.Group()
explosions = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

def spawn_enemy():
    enemy = Enemy()
    all_sprites.add(enemy)
    enemies.add(enemy)

for i in range(8):
    spawn_enemy()

stars = [Star() for _ in range(100)]
score = 0
font = pygame.font.SysFont("Arial", 20)

# -------------------------
# Main Game Loop
# -------------------------
running = True
start_ticks = pygame.time.get_ticks()
while running:
    dt = clock.tick(60)  # Limit to 60 FPS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.shoot()

    # Update game logic
    all_sprites.update()
    explosions.update()
    for star in stars:
        star.update()
    # Bullet-enemy collisions
    hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
    for hit in hits:
        score += 10
        explosion = Explosion(hit.rect.center, ORANGE)
        all_sprites.add(explosion)
        explosions.add(explosion)
        spawn_enemy()
    if pygame.sprite.spritecollide(player, enemies, False):
        running = False  # End game on collision

    # -------------------------
    # 2D Drawing to scene_surface
    # -------------------------
    scene_surface.fill(BLACK)
    # Draw stars
    for star in stars:
        star.draw(scene_surface)
    # Draw sprites
    all_sprites.draw(scene_surface)
    # Draw score
    score_text = font.render("Score: " + str(score), True, WHITE)
    scene_surface.blit(score_text, (10, 10))

    # -------------------------
    # Update OpenGL texture from scene_surface
    # -------------------------
    # Note: pygame.image.tostring can flip vertically (3rd argument True means flip)
    texture_data = pygame.image.tostring(scene_surface, "RGBA", True)
    glBindTexture(GL_TEXTURE_2D, scene_texture)
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glBindTexture(GL_TEXTURE_2D, 0)

    # -------------------------
    # OpenGL Post‑Processing (Draw Fullscreen Quad with Shader)
    # -------------------------
    glClear(GL_COLOR_BUFFER_BIT)
    glUseProgram(shader)
    # Pass time uniform (in seconds)
    current_time = (pygame.time.get_ticks() - start_ticks) / 1000.0
    time_loc = glGetUniformLocation(shader, "time")
    glUniform1f(time_loc, current_time)
    # Bind our scene texture to texture unit 0
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, scene_texture)
    # Tell shader that “screenTexture” is texture unit 0
    tex_loc = glGetUniformLocation(shader, "screenTexture")
    glUniform1i(tex_loc, 0)
    glBindVertexArray(VAO)
    glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
    glBindVertexArray(0)
    glUseProgram(0)

    pygame.display.flip()

pygame.quit()
sys.exit()
