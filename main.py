#!/usr/bin/env python3
# Copyright (C) 2024 Dominik Holland
# SPDX-License-Identifier: GPL-3.0

from requests import Session
from copy import deepcopy
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
        print("Login on server {0}".format(self.server))
        credentials = {"username": username, "password": password}
        self.session = Session()
        resp = self.session.post(self.server + "/login", json = credentials)
        if not resp.ok:
            resp.raise_for_status()
        self.auth_token = resp.json()["token"]
        self.auth_header = {"Authorization": self.auth_token, "Content-Type": "application/json" }

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
        return resp.json()

    def unsubscribe(self, channel_id):
        print("Unsubscribe from Channel {0} on server {1}".format(channel_id, self.server))
        if dryRun:
            return;
        channel = {"channelId" : channel_id}
        resp = self.session.post(self.server + "/unsubscribe", json = channel, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

    def getPlaylists(self):
        resp = self.session.get(self.server + "/user/playlists", headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return list({"id": sub["id"], "name": sub["name"] } for sub in resp.json())

    def createPlaylist(self, name):
        print("Create new playlist {0} on server {1}".format(name, self.server))
        if dryRun:
            return { "playlistId" : "test_id" };
        playlist = {"name" : name}
        resp = self.session.post(self.server + "/user/playlists/create", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

    def deletePlaylist(self, playlist_id):
        print("Delete playlist {0} on server {1}".format(playlist_id, self.server))
        if dryRun:
            return;
        playlist = {"playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/delete", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

    def renamePlaylist(self, playlist_id, new_name):
        playlist = {"playlistId" : playlist_id, "newName": new_name}
        if dryRun:
            return;
        resp = self.session.post(self.server + "/user/playlists/rename", json = playlist, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

    def clearPlaylist(self, playlist_id):
        print("Clear playlist {0} on server {1}".format(playlist_id, self.server))
        if dryRun:
            return;
        item = {"playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/clear", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

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
        return resp.json()

    def addPlaylistItems(self, playlist_id, videoIds):
        print("Add the following items to playlist {0} on server {1}".format(playlist_id, self.server))
        print(videoIds)
        if dryRun:
            return;
        item = {"videoIds" : videoIds, "playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/add", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

    def removePlaylistItem(self, playlist_id, index):
        print("Remove index {0} from playlist {1} on server {2}".format(index, playlist_id, self.server))
        if dryRun:
            return;
        item = {"index" : index, "playlistId" : playlist_id}
        resp = self.session.post(self.server + "/user/playlists/remove", json = item, headers = self.auth_header)
        if not resp.ok:
            resp.raise_for_status()
        return resp.json()

class Sync:
    servers = []
    leftOverTodos = []

    def __init__(self):
        try:
            with open('state.json') as f:
                self.state = json.load(f)
                self.state.setdefault("subscriptions", [])
                self.state.setdefault("servers", [])
                self.state.setdefault("playlists", [])
                self.state.setdefault("todo", [])
                f.close()
        except FileNotFoundError:
            self.state = {
                "subscriptions": [],
                "servers": [],
                "playlists": [],
                "todo": [],
            }
        try:
            with open('config.json') as f:
                self.config = json.load(f)
                f.close()
        except:
            raise ValueError("Could not open config.json")

        # Save all leftover todos in a extra list
        # This is needed to ignore certain changes if there are open todos
        self.leftOverTodos = deepcopy(self.state["todo"])

        # Create a new state to store updates
        self.newState = deepcopy(self.state)

        for server in self.config["servers"]:
            serverObj = Server(server["url"])
            serverObj.login(server["username"], server["password"])
            self.servers.append(serverObj)


    def addTodo(self, type, additionalKey, additionalValue, serverFilter):
        servers = [i for i, s in enumerate(self.servers) if s not in serverFilter]
        found = False
        for index, value in enumerate(self.newState["todo"]):
            if value['type'] == type and value[additionalKey] == additionalValue:
                value['servers'] = list(set(value['servers'] + servers))
                found = True
                break
        if not found:
            self.newState["todo"].append({ 'type': type, additionalKey: additionalValue, 'servers': servers })

    def hasLeftOverTodo(self, type, server):
        for index, value in enumerate(self.leftOverTodos):
            if value['type'] == type and self.servers.index(server) in value['servers']:
                return True
        return False

    def subscribe(self, serverFilter, channel_id):
        subscriptions = self.newState["subscriptions"]
        subscriptions.append(channel_id)
        self.newState["subscriptions"] = subscriptions
        self.addTodo("subscribe", "channel", channel_id, serverFilter)

    def unsubscribe(self, serverFilter, channel_id):
        if self.hasLeftOverTodo("subscribe", serverFilter[0]):
            print("Server state not uptodate: Ignore unsubscribe from server {0}".format(serverFilter[0].url))
            return;
        subscriptions = self.newState["subscriptions"]
        subscriptions.remove(channel_id)
        self.newState["subscriptions"] = subscriptions
        self.addTodo("unsubscribe", "channel", channel_id, serverFilter)

    def deletePlaylist(self, serverFilter, name):
        if self.hasLeftOverTodo("createPlaylist", serverFilter[0]):
            print("Server state not uptodate: Ignore deletePlaylist of {0} from server {1}".format(name, serverFilter[0].url))
            return;
        self.newState["playlists"] = [p for p in self.newState["playlists"] if not p["name"] == name]
        self.addTodo("deletePlaylist", "name", name, serverFilter)

    def createPlaylist(self, serverFilter, name, items):
        if self.hasLeftOverTodo("deletePlaylist", serverFilter[0]):
            print("Server state not uptodate: Ignore createPlaylist of {0} from server {1}".format(name, serverFilter[0]))
            return;
        playlists = self.newState["playlists"]
        playlists.append({'name': name, 'items': items})
        self.newState["playlists"] = playlists
        self.addTodo("createPlaylist", "name", name, serverFilter)

    def addPlaylistItem(self, serverFilter, name, item, index):
        servers = [s.url for i, s in enumerate(self.servers) if s not in serverFilter]
        print("TODO: Add Playlist Item {0} at {1} to Playlist {2} on servers {3}".format(item, index, name, servers))
        playlists = self.newState["playlists"]
        for idx, p in enumerate(playlists):
            if p["name"] == name:
                new_list = p["items"]
                new_list.insert(index, item)
                playlists[idx] = {'name': name, 'items': new_list}
        self.newState["playlists"] = playlists
        self.addTodo("updatePlaylist", "name", name, serverFilter)

    def removePlaylistItem(self, serverFilter, name, item, index):
        if self.hasLeftOverTodo("updatePlaylist", serverFilter[0]):
            print("Server state not uptodate: Ignore removing Playlist Item from server {0}".format(serverFilter[0].url))
            return;
        servers = [s.url for i, s in enumerate(self.servers) if s not in serverFilter]
        print("TODO: Remove Playlist Item {0} at {1} to Playlist {2} on servers {3}".format(item, index, name, servers))
        playlists = self.newState["playlists"]
        for idx, p in enumerate(playlists):
            if p["name"] == name:
                new_list = p["items"]
                if item in new_list:
                    new_list.remove(item)
                playlists[idx] = {'name': name, 'items': new_list}
        self.newState["playlists"] = playlists
        self.addTodo("updatePlaylist", "name", name, serverFilter)

    def pushCurrentState(self, serverObj):
        print("Pushing current State to {0}".format(serverObj.url))
        for sub in self.newState["subscriptions"]:
            serverObj.subscribe(sub);
        for p in self.newState["playlists"]:
            response = serverObj.createPlaylist(p["name"]);
            playlist_id = response['playlistId']
            serverObj.addPlaylistItems(playlist_id, p["items"])

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

    def detectItemChange(self, original_list, new_list, addItemAction, removeItemAction):
        for idx, item in enumerate(new_list):
            if new_list[idx] not in original_list:
                addItemAction(idx, item)
        for idx, item in enumerate(original_list):
            if original_list[idx] not in new_list:
                removeItemAction(idx, item)

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

            for p in playlists:
                name = p["name"]
                playlist_id = p["id"]
                saved_content = next(x["items"] for x in self.state["playlists"] if x["name"] == name)
                new_content_id = next(x["id"] for x in playlists if x["name"] == name)
                new_content = serverObj.getPlaylistItems(new_content_id)

                print("Checking playlist {0} for new/removed items on server {1}".format(name, serverObj.url))
                self.detectItemChange(saved_content, new_content,
                    lambda idx, item: self.addPlaylistItem([serverObj], name, item, idx),
                    lambda idx, item: self.removePlaylistItem([serverObj], name, item, idx)
                )

            if not serverObj.url in self.state["servers"]:
                servers = self.state["servers"]
                servers.append(serverObj.url)
                self.state["servers"] = servers

        # Change detection done. Save the new state
        self.state = deepcopy(self.newState)

        todos = deepcopy(self.state["todo"])
        self.state["todo"] = []
        # print("OPEN TODOS:", todos)
        while todos:
            action = todos.pop()
            print("Processing todo:", action)
            serverList = deepcopy(action["servers"])
            action["servers"] = []
            while serverList:
                server = serverList.pop()
                try:
                    serverObj = self.servers[server]
                    if action["type"] == "subscribe":
                        serverObj.subscribe(action["channel"])
                    elif action["type"] == "unsubscribe":
                        serverObj.unsubscribe(action["channel"])
                    elif action["type"] == "deletePlaylist":
                        playlists = serverObj.getPlaylists()
                        for sp in playlists:
                            if sp["name"] == action["name"]:
                                serverObj.deletePlaylist(sp["id"])
                    elif action["type"] == "createPlaylist":
                        for idx, p in enumerate(self.state["playlists"]):
                            if p["name"] == action["name"]:
                                response = serverObj.createPlaylist(action["name"])
                                playlist_id = response['playlistId']
                                if len(p["items"]) != 0:
                                    serverObj.addPlaylistItems(playlist_id, p["items"])
                    elif action["type"] == "updatePlaylist":
                        for idx, p in enumerate(self.state["playlists"]):
                            if p["name"] == action["name"]:
                                playlist_updated = False;
                                playlists = serverObj.getPlaylists()
                                for sp in playlists:
                                    if sp["name"] == action["name"]:
                                        serverObj.clearPlaylist(sp["id"])
                                        serverObj.addPlaylistItems(sp["id"], p["items"])
                                        new_content = serverObj.getPlaylistItems(sp["id"])
                                        if new_content != p["items"]:
                                            print("Couldn't update playlist {0} on server {1}. Try again in next sync.".format(action["name"], serverObj.url))
                                            raise ValueError("Server refused update")
                                        playlist_updated = True
                                if not playlist_updated:
                                    print("Couldn't find playlist {0} on server {1}. Creating it now.".format(action["name"], serverObj.url))
                                    response = serverObj.createPlaylist(action["name"])
                                    playlist_id = response['playlistId']
                                    serverObj.addPlaylistItems(playlist_id, p["items"])
                    else:
                        print("Unknown todo type:", action["type"])
                except:
                    print("Failed to send todo to server", self.servers[server].url)
                    # save the current server back into the action
                    newServerList = action["servers"]
                    newServerList.append(server)
                    action["servers"] = newServerList

            # If we have some servers again in the action something didn't work
            # and we need to save the action again as todo
            if len(action["servers"]) > 0:
                newTodos = self.state["todo"]
                newTodos.append(action)
                self.state["todo"] = newTodos

        if not dryRun:
            try:
                with open('state.json', 'w+') as f:
                    json.dump(self.state, f)
                    f.close()
            except:
                raise ValueError("Could not write config.json")

Sync().sync()

