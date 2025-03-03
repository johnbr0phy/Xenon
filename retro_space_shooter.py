import pygame
import random
import sys

# Initialize pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Shooter: Xenon 2 Inspired")

# Clock for FPS control
clock = pygame.time.Clock()

# ----- Asset Creation Functions -----
def create_player_asset():
    """Generate a simple triangular spaceship for the player."""
    surface = pygame.Surface((40, 40), pygame.SRCALPHA)
    # Draw a triangle (ship) with the tip pointing up
    pygame.draw.polygon(surface, GREEN, [(20, 0), (0, 40), (40, 40)])
    return surface

def create_enemy_asset():
    """Generate a simple enemy ship asset."""
    surface = pygame.Surface((30, 30), pygame.SRCALPHA)
    # Draw a rectangle and a small triangle on top for a retro look
    pygame.draw.rect(surface, RED, (5, 5, 20, 20))
    pygame.draw.polygon(surface, YELLOW, [(15, 0), (5, 5), (25, 5)])
    return surface

def create_bullet_asset():
    """Generate a bullet asset."""
    surface = pygame.Surface((5, 10), pygame.SRCALPHA)
    pygame.draw.rect(surface, YELLOW, (0, 0, 5, 10))
    return surface

# ----- Sprite Classes -----
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = create_player_asset()
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 10
        self.speed = 5
        self.shoot_delay = 250  # milliseconds between shots
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

        # Keep the player within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

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
        # If the enemy goes off screen, respawn at the top with new random properties
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
        self.speedy = -10  # Bullet moves upward

    def update(self):
        self.rect.y += self.speedy
        # Remove bullet if it goes off the top of the screen
        if self.rect.bottom < 0:
            self.kill()

# ----- Star Background -----
class Star:
    def __init__(self):
        self.x = random.randrange(0, SCREEN_WIDTH)
        self.y = random.randrange(0, SCREEN_HEIGHT)
        self.speed = random.randrange(1, 4)

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randrange(0, SCREEN_WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (self.x, self.y), 2)

# Create a list of stars for the background
stars = [Star() for _ in range(50)]

# ----- Sprite Groups -----
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()

# Create player instance and add to the sprite group
player = Player()
all_sprites.add(player)

# Function to spawn an enemy ship
def spawn_enemy():
    enemy = Enemy()
    all_sprites.add(enemy)
    enemies.add(enemy)

# Spawn a few initial enemies
for i in range(8):
    spawn_enemy()

# Score and font setup
score = 0
font = pygame.font.SysFont("Arial", 20)

# ----- Main Game Loop -----
running = True
while running:
    clock.tick(60)  # Limit to 60 frames per second

    # Process input (events)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Player shoots when space is pressed
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.shoot()

    # Update all sprites and background stars
    all_sprites.update()
    for star in stars:
        star.update()

    # Check for collisions between bullets and enemies
    hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
    for hit in hits:
        score += 10
        spawn_enemy()

    # Check for collisions between enemies and the player
    if pygame.sprite.spritecollide(player, enemies, False):
        running = False  # Game over

    # Draw everything on the screen
    screen.fill(BLACK)
    for star in stars:
        star.draw(screen)
    all_sprites.draw(screen)
    score_text = font.render("Score: " + str(score), True, WHITE)
    screen.blit(score_text, (10, 10))
    pygame.display.flip()

pygame.quit()
sys.exit()
