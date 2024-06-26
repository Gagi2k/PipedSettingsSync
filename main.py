from requests import Session
import json

# Download state from all servers and store it
# If no stored state -> push current state
# If state, compare it with stored state
# All changes are pushed to all other servers

dryRun = False;

class Server:
    def __init__(self, server):
        self.server = server

    @property
    def url(self):
        return self.server

    def login(self, username, password):
        credentials = {"username": username, "password": password}
        self.session = Session()
        resp = self.session.post(self.server + "/login", json = credentials)
        if not resp.ok:
            resp.raise_for_status()
        self.auth_token = resp.json()["token"]
        self.auth_header = {"Authorization": self.auth_token}

    def getSubscriptions(self):
        resp = self.session.get(self.server + "/subscriptions", headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return list(sub['url'].split("/")[-1] for sub in resp.json())

    def subscribe(self, channel_id):
        print("Subscribe to Channel {0} on server {1}".format(channel_id, self.server))
        if dryRun:
            return;
        channel = {"channelId" : channel_id}
        resp = self.session.post(self.server + "/subscribe", json = channel, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def unsubscribe(self, channel_id):
        print("Unsubscribe from Channel {0} on server {1}".format(channel_id, self.server))
        if dryRun:
            return;
        channel = {"channelId" : channel_id}
        resp = self.session.post(self.server + "/unsubscribe", json = channel, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def getPlaylists(self):
        resp = self.session.get(self.server + "/user/playlists", headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return list({"id": sub["id"], "name": sub["name"] } for sub in resp.json())

    def createPlaylist(self, name):
        print("Create new playlist {0} on server {1}".format(name, self.server))
        if dryRun:
            return;
        playlist = {"name" : name}
        resp = self.session.post(self.server + "/user/playlists/create", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def deletePlaylist(self, playlist_id):
        print("Delete playlist {0} on server {1}".format(playlist_id, self.server))
        if dryRun:
            return;
        playlist = {"playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/delete", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def renamePlaylist(self, playlist_id, new_name):
        playlist = {"playlistId" : playlist_id, "newName": new_name}
        if dryRun:
            return;
        resp = self.session.post(self.server + "/user/playlists/rename", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def clearPlaylist(self, playlist_id):
        print("Clear playlist {0} on server {1}".format(playlist_id, self.server))
        if dryRun:
            return;
        item = {"playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/clear", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def getPlaylistItems(self, playlist_id):
        resp = self.session.get(self.server + "/playlists/" + playlist_id, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return list(sub['url'].split('=')[-1] for sub in resp.json()["relatedStreams"])

    def addPlaylistItem(self, playlist_id, videoId):
        print("Add item {0} to playlist {1} on server {2}".format(videoId, playlist_id, self.server))
        if dryRun:
            return;
        item = {"videoId" : videoId, "playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/add", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

    def removePlaylistItem(self, playlist_id, index):
        print("Remove index {0} from playlist {1} on server {2}".format(index, playlist_id, self.server))
        if dryRun:
            return;
        item = {"index" : index, "playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/remove", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()

class Sync:
    servers = []

    def __init__(self):
        try:
            with open('state.json') as f:
                self.state = json.load(f)
                f.close()
        except:
            self.state = {
                "subscriptions": [],
                "servers": [],
                "playlists": [],
            }
        try:
            with open('config.json') as f:
                self.config = json.load(f)
                f.close()
        except:
            raise ValueError("Could not open config.json")

        for server in self.config["servers"]:
            serverObj = Server(server["url"])
            serverObj.login(server["username"], server["password"])
            self.servers.append(serverObj)

    def subscribe(self, serverFilter, channel_id):
        for serverObj in self.servers:
            if serverObj in serverFilter:
                continue
            serverObj.subscribe(channel_id)
        subscriptions = self.state["subscriptions"]
        subscriptions.append(channel_id)
        self.state["subscriptions"] = subscriptions

    def unsubscribe(self, serverFilter, channel_id):
        for serverObj in self.servers:
            if serverObj in serverFilter:
                continue
            serverObj.unsubscribe(channel_id)
        subscriptions = self.state["subscriptions"]
        subscriptions.remove(channel_id)
        self.state["subscriptions"] = subscriptions

    def deletePlaylist(self, serverFilter, name):
        for serverObj in self.servers:
            if serverObj in serverFilter:
                continue
            playlists = serverObj.getPlaylists()
            for p in playlists:
                if p["name"] == name:
                    serverObj.deletePlaylist(p["id"])
        playlists = self.state["playlists"]
        playlists.remove
        self.state["playlists"] = playlists

    def createPlaylist(self, serverFilter, name, items):
        for serverObj in self.servers:
            if serverObj in serverFilter:
                continue
            serverObj.createPlaylist(name)
            for i in items:
                serverObj.addPlaylistItem(playlist_id, i);
        playlists = self.state["playlists"]
        playlists.append({'name': name, 'items': items})
        self.state["playlists"] = playlists

    def updatePlaylist(self, serverFilter, name, items):
        for serverObj in self.servers:
            if serverObj in serverFilter:
                continue
            playlists = serverObj.getPlaylists()
            for p in playlists:
                if p["name"] == name:
                    serverObj.clearPlaylist(p["id"])
                    for i in items:
                        serverObj.createPlaylistItem(p["id"], i)
        playlists = self.state["playlists"]
        for idx, p in enumerate(playlists):
            if p["name"] == name:
                playlists[idx] = {'name': name, 'items': items}
        self.state["playlists"] = playlists

    def pushCurrentState(self, serverObj):
        print("Pushing current State to {0}".format(serverObj.url))
        for sub in self.state["subscriptions"]:
            serverObj.subscribe(sub);
        for p in self.state["playlists"]:
            serverObj.createPlaylist(p["name"]);
            # Get all playlists to find the id of the playlist we just created
            playlists = serverObj.getPlaylists();
            playlist_id = next(x["id"] for x in playlists if x["name"] == p["name"])
            for i in p["items"]:
                serverObj.addPlaylistItem(playlist_id, i);

    def detectNewItems(self, original_list, new_list, key, addItemAction):
        for idx, item in enumerate(new_list):
            if key:
                if not any(d[key] == item[key] for d in original_list):
                    addItemAction(idx, item)
            else:
                if not item in original_list:
                    addItemAction(idx, item)

    def detectRemovedItems(self, original_list, new_list, key, removeItemAction):
        for idx, item in enumerate(original_list):
            if key:
                if not any(d[key] == item[key] for d in new_list):
                    removeItemAction(idx, item)
            else:
                if not item in new_list:
                    removeItemAction(idx, item)

    def detectItemChange(self, original_list, new_list, itemsChangedAction):
        if len(original_list) != len(new_list):
            itemsChangedAction()
        for idx, item in enumerate(original_list):
            if original_list[idx] != new_list[idx]:
                itemsChangedAction()

    def sync(self):
        for serverObj in self.servers:
            subscriptions = serverObj.getSubscriptions()
            playlists = serverObj.getPlaylists()

            if serverObj.url in self.state["servers"]:
                print("Checking for removed subscriptions on server {0}".format(serverObj.url))
                self.detectRemovedItems(self.state["subscriptions"], subscriptions, None,
                    lambda idx, item : self.unsubscribe([serverObj], item)
                )
                print("Checking for removed playlists on server {0}".format(serverObj.url))
                self.detectRemovedItems(self.state["playlists"], playlists, "name",
                    lambda idx, item : self.deletePlaylist([serverObj], item["name"])
                )
            else:
                print("New server added to sync list")
                self.pushCurrentState(serverObj)

            print("Checking for new subscriptions on server {0}".format(serverObj.url))
            self.detectNewItems(self.state["subscriptions"], subscriptions, None,
                lambda idx, item : self.subscribe([serverObj], item)
            )
            print("Checking for new playlists on server {0}".format(serverObj.url))
            self.detectNewItems(self.state["playlists"], playlists, "name",
                lambda idx, item : self.createPlaylist([serverObj], item["name"], serverObj.getPlaylistItems(item["id"]))
            )


            #TODO Once playlist editing is fully implemented in Piped we can be smarter here as well
            for p in playlists:
                name = p["name"]
                playlist_id = p["id"]
                saved_content = next(x["items"] for x in self.state["playlists"] if x["name"] == name)
                new_content_id = next(x["id"] for x in playlists if x["name"] == name)
                new_content = serverObj.getPlaylistItems(new_content_id)

                print("Checking playlist {0} for new/removed items on server {1}".format(name, serverObj.url))
                self.detectItemChange(saved_content, new_content,
                    lambda : self.updatePlaylist([serverObj], name, new_content)
                )

            if not serverObj.url in self.state["servers"]:
                servers = self.state["servers"]
                servers.append(serverObj.url)
                self.state["servers"] = servers

        try:
            with open('state.json', 'w+') as f:
                json.dump(self.state, f)
                f.close()
        except:
            raise ValueError("Could not write config.json")

Sync().sync()

#TODO
# Add a transaction system
# Don't push changes if multiple instances have changes on the same thing
# Add a way to push our saved state to a server
#  Add a option to remove all things before, or just add the state
