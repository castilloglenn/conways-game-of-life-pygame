import pprint
import pygame as game
import xml.etree.ElementTree as xml
import numpy as np
from pygame import sprite
import os


# Accessing XML data and saving to a dictionary for later use
strings = {}
values = {}

stringsTree = xml.parse('strings.xml')
stringsRoot = stringsTree.getroot()
for stringsElement in stringsRoot: strings[stringsElement.tag] = stringsElement.text

valuesTree = xml.parse('values.xml')
valuesRoot = valuesTree.getroot()
for valuesElement in valuesRoot:
    if valuesElement.tag[0:3] == 'int':
        values[valuesElement.tag] = int(valuesElement.text)
    elif valuesElement.tag[0:5] == 'float':
        values[valuesElement.tag] = float(valuesElement.text)

# GLOBAL DEFAULT VARIABLES
COLOR = {'black': (0,0,0), 
         'white': (255, 255, 255)}
BACKGROUND = (0, 0, values['intScreenWidth'], values['intScreenHeight'])
clock = game.time.Clock()
previousMouseCoordinates = None

# Speed of the generation cycle
gameSpeed = values['floatGameSpeed']
ticksCounter = 0
generation = 0
timeout = 0
timeoutPeak = values['intFrameRate'] * values['intPauseTimeout']
startAtPaused = True
initialStart = True

# Cell representation is a box with the same
#   width and height determined by this variable
CELL_SIZE = values['intCellSize']

# Cells age through generations, the decay rate will
#   is included in the formula of reducing the color
CELL_DECAY_RATE = values['intCellDecayRate']

# Cells final color/state will be the value of this
#   translated into RGB, ex. 50 = (50, 50, 50)
CELL_MINIMUM_STATE = values['intCellMinimumState']

# Cell group for easier control
cellGroup = sprite.Group()

# Range of cells needed for an alive cell to remain alive
aliveRange = []
for aliveRangeValues in str(values['intAliveAdjacentCellRequirement']):
    aliveRange.append(int(aliveRangeValues))

# Range of cells needed for a dead cell to be alive
deadRange = []
for deadRangeValues in str(values['intDeadAdjacentCellRequirement']):
    deadRange.append(int(deadRangeValues))


# Logical 2D array that represents the display into a more manageable board
# Matrix board values: 0 = cell dead/unpopulated, 1 = cell alive/populated
matrix = []
emptyMatrix = []
for rows in range(values['intScreenHeight'] // CELL_SIZE):
    matrix.append([0] * (values['intScreenWidth'] // CELL_SIZE))
    emptyMatrix.append([0] * (values['intScreenWidth'] // CELL_SIZE))
nextMatrix = np.copy(matrix)


# Cells are the life forms of the game of life
class Cell(sprite.Sprite):
    def __init__(self, x, y):
        global matrix
        super().__init__()
        self.surface = game.Surface((CELL_SIZE, CELL_SIZE))
        self.rect = self.surface.get_rect()
        self.rect.x = x
        self.rect.y = y

        # All cells starts at age zero, this determines the
        #   color of the cell they will show on the display
        self.age = 0
        self.color = COLOR[strings['cellColor']]

        # Setting the matrix board coordinates based on the display location 
        self.matrixColumn = self.rect.y // CELL_SIZE
        self.matrixRow = self.rect.x // CELL_SIZE
        matrix[self.matrixColumn][self.matrixRow] = 1


    def increaseAge(self):
        self.age += 1
        decay = 255 - (values['intCellDecayRate'] * self.age)
        if decay < values['intCellMinimumState']:
            decay = values['intCellMinimumState']
        self.color = (decay, decay, decay)
        matrix[self.matrixColumn][self.matrixRow] = 1


    def die(self):
        global matrix
        self.age = 0
        # Updating the matrix board before deleting the sprite object itself
        matrix[self.matrixColumn][self.matrixRow] = 0 # not useful
        self.color = COLOR[strings['gameBackgroundColor']]


    def check(self):
        global matrix
        if matrix[self.matrixColumn][self.matrixRow] == 2:
            self.increaseAge()
        else: self.die()


    def renew(self):
        global matrix
        self.age = 0
        self.color = COLOR[strings['cellColor']]
        matrix[self.matrixColumn][self.matrixRow] = 1

    
    def update(self):
        if self.color != COLOR[strings['gameBackgroundColor']]:
            game.draw.rect(display, self.color, self.rect, 0)
    # End of Cell class


def clearResourcesAndQuit():
    game.display.quit()
    game.quit()
    quit()


def refreshDisplay():
    game.display.update()
    clock.tick(values['intFrameRate'])


def addNewCell(relativeLocation):
    # Avoiding cell duplication on the same location
    cellExists = False
    for cell in cellGroup:
        if relativeLocation == (cell.rect.x, cell.rect. y):
            cellExists = True
            cell.renew()
    # then the game will add a new cell on the location
    if not cellExists: 
        cellGroup.add(Cell(relativeLocation[0], relativeLocation[1]))


def deleteCell(relativeLocation):
    # then the game will remove that cell specified based on the
    #   relative location if the cell is active, or alive
    for cell in cellGroup:
        if relativeLocation == (cell.rect.x, cell.rect. y):
            # Updating the matrix board before deleting the sprite object itself
            matrix[cell.rect.y // CELL_SIZE][cell.rect.x // CELL_SIZE] = 0
            cell.color = COLOR[strings['gameBackgroundColor']]


def getRelativeLocation(pos):
    # This function returns the grid-relative coordinates of the
    #   specific mouse position based on the cell's square side
    modulo = (pos[0] % CELL_SIZE, pos[1] % CELL_SIZE)
    return (pos[0] - modulo[0], pos[1] - modulo[1])


def evaluateMatrixNeighbors(matrixCoordinates, isAlive):
    global matrix
    # the arrangement of the sides here are as follows:
    # North West, North, North East, West, East, South West, South and South East
    sides = ((-1, -1), (-1, 0), (-1, 1),
             ( 0, -1),          ( 0, 1),
             ( 1, -1), ( 1, 0), ( 1, 1))

    # The neighbor count will be the value to judge the cell if it survives or not
    neighborCount = 0
    for side in sides:
        target = (matrixCoordinates[0] + side[0], matrixCoordinates[1] + side[1])
        if (target[0] >= 0 and target[0] < len(matrix)) and (target[1] >= 0 and target[1] < len(matrix[0])):
            if matrix[matrixCoordinates[0] + side[0]][matrixCoordinates[1] + side[1]] == 1:
                neighborCount += 1
    
    if isAlive and neighborCount in aliveRange: nextMatrix[matrixCoordinates[0]][matrixCoordinates[1]] = 2
    elif not isAlive and neighborCount in deadRange: nextMatrix[matrixCoordinates[0]][matrixCoordinates[1]] = 2
    else: nextMatrix[matrixCoordinates[0]][matrixCoordinates[1]] = 0


def nextGeneration():
    global matrix, nextMatrix, emptyMatrix
    # The rules of Game of life is as follows:
    # Any live cell with two or three live neighbours survives.
    # Any dead cell with three live neighbours becomes a live cell.
    # All other live cells die in the next generation. Similarly, all other dead cells stay dead.

    # The rules of Game of life is as follows:
    # Any live cell with two or three live neighbours survives.
    # Any dead cell with three live neighbours becomes a live cell.
    # All other live cells die in the next generation. Similarly, all other dead cells stay dead.

    # the value 1 in our matrix board means the cell is currently alive, we will evaluate each
    # cells to determine wether they will survive the next generation, while in the process of
    # evaluation, we will temporarily place the number 2 in the board if the cell is going to survive
    # the next generation, then after evaluating the board, we will iterate through our cell group
    # the (sprite.Group) "cellGroup" list, if the cell is alive, then it will remain on the screen
    # and finally updates its value on the board with 1, so we can know what cells we need to insert
    # on the display, and those will be the remaining 2's.

    for columnIndex in range(len(matrix)):
        for rowIndex in range(len(matrix[columnIndex])):
            if matrix[columnIndex][rowIndex] == 1: evaluateMatrixNeighbors((columnIndex, rowIndex), True)
            elif matrix[columnIndex][rowIndex] == 0: evaluateMatrixNeighbors((columnIndex, rowIndex), False)

    matrix = np.copy(nextMatrix)
    nextMatrix = np.copy(emptyMatrix)

    for cell in cellGroup: cell.check()
    
    for columnCheck in range(len(matrix)):
        for rowCheck in range(len(matrix[columnCheck])):
            if matrix[columnCheck][rowCheck] == 2: 
                addNewCell((rowCheck * CELL_SIZE, columnCheck * CELL_SIZE))


def addTicks():
    global ticksCounter, matrix
    ticksCounter += 1

    # If the ticks surpasses the adjusted value
    if ticksCounter >= (values['intFrameRate'] / gameSpeed):
        global generation, matrix, initialStart

        # Update values
        ticksCounter = 0

        # This checks if there is still an active cell in the generation, if there is none,
        #   then the generation will be stopped, this is useful in testing different seeds
        if initialStart:
            # This allows the program to give an exemption because initially all cells are empty
            #   and proceed to calculate succeeding generations after
            initialStart = False
            generation += 1
            nextGeneration()
        elif 1 in matrix:
            generation += 1
            nextGeneration()


def gameMouseDownEvents(event):
    global gameSpeed

    relativeLocation = getRelativeLocation(event.pos)

    # If the user clicked on left mouse button
    if event.button == 1: addNewCell(relativeLocation)

    # If the user clicked on the right mouse button
    if event.button == 3: deleteCell(relativeLocation)

    # If the user scrolls the mouse wheel upward
    if event.button == 4: 
        # then the game speed will increment by 0.1-1 capped at the current FPS
        if gameSpeed < 1: gameSpeed += 0.1
        elif gameSpeed < values['intFrameRate']: gameSpeed += 1.0

    # If the user scrolls the mouse wheel downward
    if event.button == 5: 
        # the nthe game speed will decrement by 1-0.1 min at 0.1
        if gameSpeed > 1: gameSpeed -= 1
        elif gameSpeed > 0.1: gameSpeed -= 0.1

    # Removing excess data values resulted by the computers computation
    gameSpeed = round(gameSpeed, 1)


def gameMouseDragEvents(event):
    # This variable always saves the last mouse location to be used by the
    #   gameKeyEvents() function, because we can't always get the location
    #   of the mouse if the only event is key press
    global previousMouseCoordinates
    previousMouseCoordinates = event.pos

    # Making sure the user only holds one button at a time
    if event.buttons[0] + event.buttons[1] + event.buttons[2] == 1:
        relativeLocation = getRelativeLocation(event.pos)

        # If the user is dragging the mouse with left mouse button
        if event.buttons[0] == 1: addNewCell(relativeLocation)

        # If the user is dragging the mouse with the right mouse button
        if event.buttons[2] == 1: deleteCell(relativeLocation)


def gameKeyEvents(keys):
    # If the user pressed the "del" key, the board will reset
    if keys[game.K_DELETE]:
        global gameSpeed, generation, matrix, emptyMatrix, initialStart
        matrix = np.copy(emptyMatrix)
        sprite.Group.empty(cellGroup)
        generation = 0
        initialStart = True

    # If the user pressed the "a" key, a cell will be added to the last pointer location
    if keys[game.K_a]: addNewCell(getRelativeLocation(previousMouseCoordinates))

    # If the user pressed the "d" key, the cell in the pointer location will be removed
    if keys[game.K_d]: deleteCell(getRelativeLocation(previousMouseCoordinates))


def message(text, size, x, y, shadowed):
    # Calls a recursive call to add shadow before displaying the actual texts
    if shadowed:
        message(text, size, x + values['intFontShadow'], y + values['intFontShadow'], False)

    font = game.font.Font('arcade.ttf', size)
    surface = font.render(text, True, 
        COLOR[strings['fontForegroundColor']] if shadowed else COLOR[strings['fontBackgroundColor']])
    text_rect = surface.get_rect()
    text_rect.center = (x, y)
    display.blit(surface, text_rect)


def gamePaused():
    global timeout, timeoutPeak
    timeout = 0

    paused = True
    while paused:
        # This refreshes the display completely by displaying a black
        #   rectangular box to cover previous frame's objects
        game.draw.rect(display, COLOR[strings['gameBackgroundColor']], BACKGROUND, 0)
        cellGroup.update()

        # Text displays and information on the screen
        message(f"Generation: {generation:,}   Speed: {gameSpeed} Gen/sec", 
            values['intFontSize'], values['intScreenWidth']//2, int(values['intScreenHeight'] * 0.05), True)
        message(f"Game Paused {'(Press space bar to unpause)' if timeout > timeoutPeak else '(Unpause in ' + str(((timeoutPeak - timeout) // values['intFrameRate']) + 1) + ')'}", 
            values['intFontSize'], values['intScreenWidth']//2, int((values['intScreenHeight'] * 0.925) + values['intFontSize']), True)

        for event in game.event.get():
            if event.type == game.QUIT: clearResourcesAndQuit()
            if event.type == game.MOUSEBUTTONDOWN: gameMouseDownEvents(event)
            if event.type == game.MOUSEMOTION: gameMouseDragEvents(event)
            
        # Key pressing events
        keys = game.key.get_pressed()

        # Avoiding instant unpause by setting an initial timeout of X second to unpause the game
        timeout += 1
        if keys[game.K_SPACE] and timeout >= (values['intFrameRate'] * values['intPauseTimeout']): 
            timeout = 0
            paused = False
        else: gameKeyEvents(keys)  
                    
        refreshDisplay()


if __name__ == '__main__':
    # Centering the game window on the screen
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    # Pygame initialization process
    game.init()
    game.display.set_caption(strings['gameTitle'])
    display = game.display.set_mode((values['intScreenWidth'], values['intScreenHeight']))

    # Game loop
    while True:
        # The game will start on paused for the user to setup the initial cells location
        #   for the game to be played by itself through generations
        if startAtPaused:
            startAtPaused = False
            gamePaused()

        # This refreshes the display completely by displaying a black
        #   rectangular box to cover previous frame's objects
        game.draw.rect(display, COLOR[strings['gameBackgroundColor']], BACKGROUND, 0)
        cellGroup.update()

        # Text displays and information on the screen
        message(f"Generation: {generation:,}   Speed: {gameSpeed} Gen/sec", 
            values['intFontSize'], values['intScreenWidth']//2, int(values['intScreenHeight'] * 0.05), True)
        message(f"{'Press space bar to pause' if timeout > timeoutPeak else '(Pause available in ' + str(((timeoutPeak - timeout) // values['intFrameRate']) + 1) + ')'}", 
            values['intFontSize'], values['intScreenWidth']//2, int((values['intScreenHeight'] * 0.925) + values['intFontSize']), True)

        for event in game.event.get():
            if event.type == game.QUIT: clearResourcesAndQuit()
            if event.type == game.MOUSEBUTTONDOWN: gameMouseDownEvents(event)
            if event.type == game.MOUSEMOTION: gameMouseDragEvents(event)
        
        # Key pressing events
        keys = game.key.get_pressed()

        # Avoiding instant unpause by setting an initial timeout of X second to pause the game
        timeout += 1
        if keys[game.K_SPACE] and timeout >= (values['intFrameRate'] * values['intPauseTimeout']): gamePaused()
        else: gameKeyEvents(keys)  

        refreshDisplay()
        # These ticks calculate when to update to next generation based on the
        #   game speed, ex. 1.0 means 1 generation per second, based on the fps
        addTicks()
