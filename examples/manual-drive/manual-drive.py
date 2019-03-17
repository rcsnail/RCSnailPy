import asyncio
import os
from getpass import getpass
from rcsnail import RCSnail, RCSLiveSession
import time
import pygame

FPS = 30
window_width = 960
window_height = 480
black = (0, 0, 0)
green = (0, 255, 0)
red = (255, 0, 0)

class Car:
    def __init__(self):
        # units in percentage range 0..1 
        self.steering = 0.0
        self.acceleration = 0.0
        self.braking = 0.0
        self.gear = 0
        self.max_steering = 1.0
        self.max_acceleration = 1.0
        self.max_braking = 1.0
        self.braking_k = 2.0            # coef used for virtual speed braking calc 
        self.min_deacceleration = 0.3   # speed reduction when nothing is pressed
        # units of change over one second:
        self.steering_speed = 5.0 
        self.steering_speed_neutral = 3.0 
        self.acceleration_speed = 5.0
        self.deacceleration_speed = 2.0
        self.braking_speed = 5.0
        # virtual speed
        self.virtual_speed = 0.0
        self.max_virtual_speed =  5.0
        # key states
        self.left_down = False
        self.right_down = False
        self.up_down = False
        self.down_down = False

    def update(self, dt):
        # calculate steering
        if (not self.left_down) and (not self.right_down):
            # free center positioning
            if self.steering > 0:
                self.steering = max(0.0, self.steering - dt * self.steering_speed_neutral)
            else:
                self.steering = min(0.0, self.steering + dt * self.steering_speed_neutral)
        elif self.left_down and not self.right_down:
            self.steering = max(-1.0, self.steering - dt * self.steering_speed)
        elif not self.left_down and self.right_down:
            self.steering = min(1.0, self.steering + dt * self.steering_speed)

        # calculating gear, acceleration, braking
        if self.up_down and not self.down_down:
            if self.gear == 0:
                self.gear = 1
                self.acceleration = 0.0
            if self.gear == 1:     # drive accelerating
                self.acceleration = min(self.max_acceleration, self.acceleration + dt * self.acceleration_speed)
                self.braking = 0.0
            elif self.gear == -1:  # reverse braking
                self.braking = min(self.max_braking, self.braking + dt * self.braking_speed)
                self.acceleration = 0.0
        elif not self.up_down and self.down_down:
            if self.gear == 0:
                self.gear = -1
                self.acceleration = 0.0
            if self.gear == 1:     # drive braking
                self.braking = min(self.max_braking, self.braking + dt * self.braking_speed)
                self.acceleration = 0.0
            elif self.gear == -1:  # reverse accelerating
                self.acceleration = min(self.max_acceleration, self.acceleration + dt * self.acceleration_speed)
                self.braking = 0.0
        else:  # both down or both up
            self.acceleration = max(0.0, self.acceleration - dt * self.deacceleration_speed)
            self.braking = max(0.0, self.braking - dt * self.deacceleration_speed)

        # calculate virtual speed
        if self.up_down == self.down_down:
            # nothing or both pressed
            self.virtual_speed = max(0.0, min(self.max_virtual_speed, 
                self.virtual_speed - dt * self.min_deacceleration))
        else:
            self.virtual_speed = max(0.0, min(self.max_virtual_speed, 
                self.virtual_speed + dt * (self.acceleration - self.braking_k * self.braking)))
        
        # conditions to change the direction
        if not self.up_down and not self.down_down and self.virtual_speed < 1.0:
            self.gear = 0


    def draw(self, screen):
        # Steering gauge:
        if self.steering < 0:
            R = pygame.Rect((self.steering + 1.0) / 2.0 * window_width, 
                window_height - 10, 
                -self.steering * window_width / 2, 
                10)
        else:
            R = pygame.Rect(window_width / 2, 
                window_height - 10, 
                self.steering * window_width / 2, 
                10)
        pygame.draw.rect(screen, green, R)

        # Acceleration/braking gauge:
        if self.gear == 1:
            if self.acceleration > 0.0:
                R = pygame.Rect(window_width - 20, 
                    0,
                    10,
                    window_height / 2 * self.acceleration / self.max_acceleration)
                R = R.move(0, window_height / 2 - R.height)
                pygame.draw.rect(screen, green, R)
            if self.braking > 0.0:
                R = pygame.Rect(window_width - 20, 
                    window_height / 2,
                    10,
                    window_height / 2 * self.braking / self.max_braking)
                pygame.draw.rect(screen, red, R)
        elif self.gear == -1:
            if self.acceleration > 0.0:
                R = pygame.Rect(window_width - 20, 
                    window_height / 2,
                    10,
                    window_height / 2 * self.acceleration / self.max_acceleration)
                pygame.draw.rect(screen, green, R)
            if self.braking > 0.0:
                R = pygame.Rect(window_width - 20, 
                    0,
                    10,
                    window_height / 2 * self.braking / self.max_braking)
                R = R.move(0, window_height / 2 - R.height)
                pygame.draw.rect(screen, red, R)
        
        # Speed gauge:
        if self.virtual_speed > 0.0:
            R = pygame.Rect(window_width - 10,
                0,
                10,
                window_height * self.virtual_speed / self.max_virtual_speed)
            if self.gear >= 0:
                R = R.move(0, window_height - R.height)
            pygame.draw.rect(screen, green, R)


def pygame_event_loop(loop, event_queue):
    while True:
        event = pygame.event.wait()
        asyncio.run_coroutine_threadsafe(event_queue.put(event), loop=loop)

async def handle_pygame_events(event_queue, car):
    while True:
        event = await event_queue.get()
        if event.type == pygame.QUIT:
            break
        elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                car.left_down = event.type == pygame.KEYDOWN
            elif event.key == pygame.K_RIGHT:
                car.right_down = event.type == pygame.KEYDOWN
            elif event.key == pygame.K_UP:
                car.up_down = event.type == pygame.KEYDOWN
            elif event.key == pygame.K_DOWN:
                car.down_down = event.type == pygame.KEYDOWN
        # print("event", event)
    asyncio.get_event_loop().stop()


async def render(screen, car):
    current_time = 0
    while True:
        last_time, current_time = current_time, time.time()
        await asyncio.sleep(1 / FPS - (current_time - last_time))  # tick
        car.update((current_time - last_time) / 1.0)
        screen.fill(black)
        car.draw(screen)
        pygame.display.flip()


def main():
    print('RCSnail manual drive demo')
    username = os.getenv('RCS_USERNAME', '')
    password = os.getenv('RCS_PASSWORD', '')
    if username == '':
        username = input('Username: ')
    if password == '':
        password = getpass('Password: ')
    rcs = RCSnail()
    rcs.sign_in_with_email_and_password(username, password)

    loop = asyncio.get_event_loop()
    pygame_event_queue = asyncio.Queue()

    pygame.init()

    pygame.display.set_caption("RCSnail API manual drive demo")
    screen = pygame.display.set_mode((window_width, window_height))

    car = Car()

    pygame_task = loop.run_in_executor(None, pygame_event_loop, loop, pygame_event_queue)
    render_task = asyncio.ensure_future(render(screen, car))
    event_task = asyncio.ensure_future(handle_pygame_events(pygame_event_queue, car))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        pygame_task.cancel()
        render_task.cancel()
        event_task.cancel()
        pygame.quit()


if __name__ == "__main__":
    main()