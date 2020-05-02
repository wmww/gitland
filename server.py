#!/usr/bin/env python3
# Abandon all hope, ye who scroll down here.

# No, seriously. The only thing I cared about while writing
# this was getting it done quickly.

import os, requests, time, re, sys, shutil
from concurrent import futures
from collections import Counter

class GameServer:
    def log(self, text, mode="a"):
        open("log", mode).write(text + "\n")
        print(text)

    def gameLogic(self):
        self.log("last turn log:", mode = "w")
        self.addPlayers()
        self.updateGameState()

    def gameUpdate(self):
        os.system("git add -A")
        os.system("git commit -m \"next turn\"")
        os.system("git push origin master")

    def addPlayers(self):
        # players request to join via issue
        try:
            joinRequests = requests.get(
                "https://api.github.com/repos/programical/gitland/issues?state=open",
                headers={"Accept":"application/vnd.github.v3+json", "Cache-Control": "no-cache", "Pragma": "no-cache"}
            ).json()
        except Exception:
            print("connection issues - waiting")
            time.sleep(30)
            return

        for request in joinRequests:
            try:
                newPlayer = request["user"]["login"]
                title = request["title"]
            except TypeError:
                self.log("too many API requests - can't add players")
                return

            if title == "leave":
                self.clearPlayerData(newPlayer)
                continue
            elif title == 'join':
                # select team with fewest members
                team = self.getTeamCounts().most_common()[-1][0]
            elif title in {'cr', 'cg', 'cb'}:
                team = title
            else:
                continue  # unrelated issue

            # make sure they aren't already playing
            playing = False
            for player in os.listdir("players"):
                if player == newPlayer:
                    playing = True
                    break

            if playing:
                self.log(newPlayer + " didn't join - already playing")
                continue

            self.spawnPlayer(newPlayer, team)

    def addPlayerData(self, player: str, team: str, x: int, y: int):
        os.makedirs("players/" + player)
        open("players/" + player + "/team", "w").write(team)
        open("players/" + player + "/x", "w").write(str(x))
        open("players/" + player + "/y", "w").write(str(y))
        open("players/" + player + "/timestamp", "w").write(str(time.time()))

    def clearPlayerData(self, player: str):
        if player.strip() != "" and os.path.isdir("./players/" + player):
            shutil.rmtree("./players/" + player)
            self.log(player + " left the game")
        else:
            self.log(player + " didn't leave - no player info found")

    def spawnPlayer(self, player: str, team: str):
        # spawn in friendly territory
        x, y = 0, 0
        for row in open("map").read().split("\n"):
            x = 0
            for tile in row.split(","):
                teamTile = team.replace("c", "u") # lazy hack
                if tile == teamTile:
                    self.addPlayerData(player, team, x, y)
                    self.log(player + " joined " + team + " on " + teamTile + " " + str(x) + "/" + str(y))
                    return

                x += 1
            y += 1

        # if that fails, try no man's land
        x, y = 0, 0
        for row in open("map").read().split("\n"):
            x = 0
            for tile in row.split(","):
                if tile == "ux":
                    self.addPlayerData(player, team, x, y)
                    self.log(player + " joined " + team + " on ux " + str(x) + "/" + str(y))
                    return

                x += 1
            y += 1

        # failed. print the team too, for debug purposes
        self.log(player + " didn't join " + team + " - no free space")

    def loadMap(self, file = "map") -> list:
        world = []
        for row in open(file).read().strip().split("\n"):
            world.append(row.split(","))

        return world

    def saveMap(self, world: list, file = "map"):
        open(file, "w").write(self.mapToStr(world))

    def drawMap(self, world: list):
        # in no way can this ever backfire
        mapStr = self.mapToStr(world).replace("ux", "![](icons/ux)").replace("ug", "![](icons/ug)").replace("ur", "![](icons/ur)").replace("ub", "![](icons/ub)").replace("cg", "![](icons/cg)").replace("cr", "![](icons/cr)").replace("cb", "![](icons/cb)").replace(",", " ").strip().replace("\n", "  \n")
        red = round((mapStr.count("cr") + mapStr.count("ur")) / 529 * 100)
        blue = round((mapStr.count("cb") + mapStr.count("ub")) / 529 * 100)
        green = round((mapStr.count("cg") + mapStr.count("ug")) / 529 * 100)
        open("README.md", "w").write(
            mapStr + "\n\n**R:** " + str(red) + "% **G:** " + str(green) + "% **B:** " + str(blue) + "%\n" + open("tutorial").read()
        )

    def mapToStr(self, world: list) -> str:
        mapString = ""
        for row in world:
            mapString += ",".join(row) + "\n"
        return mapString.strip()

    def movePlayer(self, playerToMove: str, x: int, y: int):
        if x < 0 or y < 0 or x > 22 or y > 22:
            self.log(playerToMove + " tried to walk out of the map")
            return

        for player in os.listdir("players"):
            if os.path.isdir("players/" + player) and player != playerToMove:
                occupiedX = int(open("players/" + player + "/x").read().strip())
                occupiedY = int(open("players/" + player + "/y").read().strip())
                if x == occupiedX and y == occupiedY:
                    self.log(playerToMove + " bumped into " + player)
                    return

        open("players/" + playerToMove + "/x", "w").write(str(x))
        open("players/" + playerToMove + "/y", "w").write(str(y))
        open("players/" + playerToMove + "/timestamp", "w").write(str(time.time()))
        self.log(playerToMove + " moved to " + str(x) + "/" + str(y))

    def getPlayerAction(self, player: str):
        html = requests.get(
            "https://github.com/" + player + "/gitland-client/blob/master/act",
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
        ).text
        action = re.findall(r'blob-code-inner .*>(.*)<', html)
        if action:
            return action[0].strip()
        else:
            print('failed to find action in HTML for player ' + player)
            return ''

    def getAllPlayerActions(self) -> dict:
        executor = futures.ThreadPoolExecutor()
        requests = {}
        for player in os.listdir("players"):
            if os.path.isdir("players/" + player):
                 request = executor.submit(lambda: self.getPlayerAction(player))
                 requests[player] = request
        actions = {}
        for player, request in requests.items():
            actions[player] = request.result()
        return actions

    def updateGameState(self):
        world = self.loadMap()
        decay = self.loadMap(file = "decay")

        # don't carry over player position data, only control
        x, y = 0, 0
        for row in world:
            x = 0
            for tile in row:
                world[y][x] = tile.replace("cg", "ug").replace("cb", "ub").replace("cr", "ur")
                x += 1
            y += 1

        for player in os.listdir("players"):
            if os.path.isdir("players/" + player):
                x = int(open("players/" + player + "/x").read().strip())
                y = int(open("players/" + player + "/y").read().strip())
                if not os.path.isfile("players/" + player + "/timestamp"):
                    open("players/" + player + "/timestamp", "w").write(str(time.time()))
                lastActive = float(open("players/" + player + "/timestamp").read().strip())
                kick = False

                # player input
                action = self.getPlayerAction(player)

                if action == "left":
                    self.movePlayer(player, x - 1, y)
                elif action == "right":
                    self.movePlayer(player, x + 1, y)
                elif action == "up":
                    self.movePlayer(player, x, y - 1)
                elif action == "down":
                    self.movePlayer(player, x, y + 1)
                elif action == "idle":
                    self.log(player + " didn't do anything")
                else:
                    if time.time() - lastActive > 86400: # 24h
                        self.log(player + " was kicked - no valid command for 24 hours")
                        kick = True
                    else:
                        self.log(player + " isn't playing")

                # reload after player moves
                icon = open("players/" + player + "/team").read().strip()
                x = int(open("players/" + player + "/x").read().strip())
                y = int(open("players/" + player + "/y").read().strip())

                # kick inactive players
                if time.time() - lastActive > 259200: # 72h
                    self.log(player + " was kicked - no activity for 72 hours")
                    kick = True
                if kick:
                    self.clearPlayerData(player)
                    icon = icon.replace("c", "u")

                world[y][x] = icon

        # tile decay
        x, y = 0, 0
        for row in decay:
            x = 0
            for tile in row:
                if "c" in world[y][x]:
                    decay[y][x] = "90"
                elif int(tile) <= 0:
                    self.log("tile " + str(x) + "/" + str(y) + " was lost due to decay")
                    world[y][x] = "ux"
                    decay[y][x] = "90"
                else:
                    decay[y][x] = str(int(decay[y][x]) - 1)
                x += 1
            y += 1

        self.saveMap(decay, file = "decay")
        self.saveMap(world)
        self.drawMap(world)

    def getTeamCounts(self) -> Counter:
        counts = Counter()

        for player in os.listdir("players"):
            if os.path.isdir("players/" + player):
                with open("players/" + player + "/team") as team_file:
                    counts.update([team_file.read().strip()])

        return counts


def main():
    server = GameServer()
    if sys.argv[1] == "pre":
        server.gameLogic()
    else:
        server.gameUpdate()


if __name__ == "__main__":
    main()
