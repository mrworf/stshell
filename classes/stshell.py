import sys
import os
import requests
import json
import re

class STServer:
    TYPE_SA = 1
    TYPE_DTH = 2

    UPLOAD_TYPE = {
        'OTHER'     : 'other',
        'IMAGE'     : 'images',
        'CSS'       : 'css',
        'I18N'      : 'i18n',
        'JAVASCRIPT': 'javascript',
        'VIEW'      : 'view'
    }

    URL_PATH = {}
    URL_PATH['login'] = '/j_spring_security_check'
    URL_PATH['smartapps'] = '/ide/apps'
    URL_PATH['smartapp-resources'] = '/ide/app/getResourceList'
    URL_PATH['smartapp-download'] = '/ide/app/getCodeForResource'
    URL_PATH['smartapp-create'] = '/ide/app/saveFromCode'
    URL_PATH['smartapp-upload'] = '/ide/app/uploadResources'
    URL_PATH['smartapp-editor'] = '/ide/app/editor/'
    URL_PATH['smartapp-delete'] = '/ide/app/deleteResource'
    URL_PATH['smartapp-destroy'] = '/ide/app/delete/'
    URL_PATH['smartapp-update'] = '/ide/app/compile'
    URL_PATH['smartapp-publish'] = '/ide/app/publishAjax'

    URL_PATH['devicetypes'] = '/ide/devices'
    URL_PATH['devicetype-resources'] = '/ide/device/getResourceList'
    URL_PATH['devicetype-download'] = '/ide/device/getCodeForResource'
    URL_PATH['devicetype-upload'] = '/ide/device/uploadResources'
    URL_PATH['devicetype-editor'] = '/ide/device/editor/'
    URL_PATH['devicetype-delete'] = '/ide/device/deleteResource'
    URL_PATH['devicetype-create'] = '/ide/device/saveFromCode'
    URL_PATH['devicetype-destroy'] = '/ide/device/update'
    URL_PATH['devicetype-update'] = '/ide/device/compile'
    URL_PATH['devicetype-publish'] = '/ide/device/publishAjax'

    def __init__(self, username, password, baseUrl):
        self.URL_BASE = baseUrl
        self.USERNAME = username
        self.PASSWORD = password
        self.session = requests.Session()

    def resolve(self, type=None):
        if type is None:
            return self.URL_BASE
        return "%s/%s" % (self.URL_BASE, self.URL_PATH[type])

    def login(self):
        post = {"j_username" : self.USERNAME, "j_password" : self.PASSWORD}
        r = self.session.post(self.resolve("login"), data=post, cookies={}, allow_redirects=False)
        if r.status_code == 302 and "authfail" not in r.headers["Location"]:
            return True
        return False

    def listSmartApps(self):
        """
        " Returns a hashmap with the ID of the app as key and the name and namespace
        """
        r = self.session.post(self.resolve("smartapps"))
        if r.status_code != 200:
            print "ERROR: Failed to get smartapps list"
            return None

        apps = re.compile('\<a href="/ide/app/editor/([^"]+)".*?\>\<img .+?\>\s*(.+?)\s*:\s*(.+?)\</a\>', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        lst = apps.findall(r.text)

        result = {}
        if lst is not None:
            for i in lst:
                result[i[0]] = {'id' : i[0], 'namespace' : i[1], 'name' : i[2]}
        return result

    def listDeviceTypes(self):
        """
        " Returns a hashmap with the ID of the app as key and the name and namespace
        """
        r = self.session.post(self.resolve("devicetypes"))
        if r.status_code != 200:
            print "ERROR: Failed to get smartapps list"
            return None

        apps = re.compile('\<a href="/ide/device/editor/([^"]+)".*?\>\s*(.+?)\s*:\s*(.+?)\</a\>', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        lst = apps.findall(r.text)

        result = {}
        if lst is not None:
            for i in lst:
                result[i[0]] = {'id' : i[0], 'namespace' : i[1], 'name' : i[2]}
        return result

    def __lister__(self, details, path, lst):
        for d in details:
            if "id" in d.keys():
                lst[d["id"]] = path + "/" + d["text"]
            elif "children" in d.keys():
                lst = self.__lister__(d["children"], path + "/" + d["text"], lst)
        return lst

    def getFileDetails(self, path, uuid):
        """ Returns a list of files contained in this smartapp """
        r = self.session.post(self.resolve(path), params={"id" : uuid})
        if r.status_code != 200:
            return None

        lst = self.__lister__(r.json(), "", {})

        return {"details" : r.json(), "flat" : lst }

    def getSmartAppDetails(self, smartapp):
        """ Returns a list of files contained in this smartapp """
        return self.getFileDetails("smartapp-resources", smartapp)

    def getDeviceTypeDetails(self, devicetype):
        """ Returns a list of files contained in this devicetype """
        return self.getFileDetails("devicetype-resources", devicetype)

    def __digger__(self, details, uuid, path):
        result = None
        for d in details:
            if "id" in d.keys() and d["id"] == uuid:
                return {"filename" : d["text"], "type" : d["li_attr"]["resource-type"], "content" : d["li_attr"]["resource-content-type"], "path" : path}
            elif "children" in d.keys():
                result = self.__digger__(d["children"], uuid, path + "/" + d["text"])

            if result is not None:
                break

        return result

    def getDetail(self, details, uuid):
        """ Builds a path and extracts the necessary parts to successfully download an item """
        info = self.__digger__(details, uuid, "")
        return info

    def downloadItem(self, path, owner, details, uuid):
        """ Downloads the selected item and returns it """
        details = self.getDetail(details, uuid)
        if details is None:
            print "ERROR: Unable to get details of item"
            return None

        r = self.session.post(self.resolve(path), params={"id" : owner, "resourceId" : uuid, "resourceType" : details["type"]})
        if r.status_code != 200:
            print "ERROR: Unable to download item"
            return None

        details["data"] = r.content
        return details

    def createSmartApp(self, content):
        payload = {"fromCodeType" : "code", "create" : "Create", "content" : content}
        r = self.session.post(self.resolve("smartapp-create"), data=payload, allow_redirects=False)
        if r.status_code != 302:
            print "ERROR: Unable to create item"
            return None

        p = re.compile('.*/ide/app/editor/([a-f0-9\-]+)', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.match(r.headers["Location"])

        return m.group(1)

    def updateSmartAppItem(self, details, smartapp, uuid, content):
        details = self.getDetail(details, uuid)
        payload = {"code" : content, "location" : "", "id" : smartapp, "resource" : uuid, "resourceType" : details["type"]}
        r = self.session.post(self.resolve("smartapp-update"), data=payload)
        if r.status_code != 200:
            print "ERROR: Unable to update item"
            return None

        return r.json()

    def updateDeviceTypeItem(self, details, device, uuid, content):
        details = self.getDetail(details, uuid)
        payload = {"code" : content, "location" : "", "id" : device, "resource" : uuid, "resourceType" : details["type"]}
        r = self.session.post(self.resolve("devicetype-update"), data=payload)
        if r.status_code != 200:
            print "ERROR: Unable to update item"
            return None

        return r.json()

    def deleteSmartApp(self, uuid):
        r = self.session.get(self.resolve("smartapp-destroy") + uuid, allow_redirects=False)
        if r.status_code == 302:
            return True
        return False

    def getSmartAppIds(self, uuid):
        r = self.session.get(self.resolve("smartapp-editor") + uuid)
        """
        ST.AppIDE.init({
                            url: '/ide/app/',
                            websocket: 'wss://ic.connect.smartthings.com:8443/',
                            client: '1af9e4e7-9a2d-47a4-9edf-c9f326642489',
                            id: '19d2016d-2337-46bc-ae0e-143e033d4a63',
                            versionId: '5d01fb38-cd7f-48b3-be2f-2509efb09020',
                            state: 'NOT_APPROVED'
                        });
        """

        p = re.compile('ST\.AppIDE\.init\(\{.+?url: \'([^\']+)\',.+?websocket: \'([^\']+)\',.+?client: \'([^\']+)\',.+?id: \'([^\']+)\',.+?versionId: \'([^\']+)\',.+?state: \'([^\']+)\'', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.search(r.text)

        if m:
            return {
                "url" : m.group(1),
                "websocket" : m.group(2),
                "client" : m.group(3),
                "id" : m.group(4),
                "versionid" : m.group(5),
                "state" : m.group(6)
            }
        return None

    """ Uploads content to server, needs special uuid which is not same as app uuid """
    def uploadSmartAppItem(self, uuid, content, filename, path, kind):
        files = {"fileData" : (filename, content)}
        data = {
            "id" : uuid,
            "file-type|" + filename : kind,
            "file-path|" + filename : path,
            "uploadResource" : "Upload"
        }

        r = self.session.post(self.resolve("smartapp-upload"), data=data, files=files)
        if r.status_code == 200:
            return True
        return False

    def deleteSmartAppItem(self, uuid, item):
        r = self.session.post(self.resolve('smartapp-delete'), data={"id" : uuid, "resourceId" : item})
        if r.status_code == 200:
            return True
        return False

    def getDeviceTypeIds(self, uuid):
        r = self.session.get(self.resolve("devicetype-editor") + uuid)
        p = re.compile('ST\.DeviceIDE\.init\(\{.+?url: \'([^\']+)\',.+?websocket: \'([^\']+)\',.+?client: \'([^\']+)\',.+?id: \'([^\']+)\'', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.search(r.text)

        if m:
            return {
                "url" : m.group(1),
                "websocket" : m.group(2),
                "client" : m.group(3),
                "id" : m.group(4),
                "versionid" : m.group(4), # Same as Id for some reason
                "state" : None
            }
        return None

    def uploadDeviceTypeItem(self, uuid, content, filename, path, kind):
        files = {"fileData" : (filename, content)}
        data = {
            "id" : uuid,
            "file-type|" + filename : kind,
            "file-path|" + filename : path,
            "uploadResource" : "Upload"
        }

        r = self.session.post(self.resolve("devicetype-upload"), data=data, files=files)
        if r.status_code == 200:
            return True
        return False

    def deleteDeviceTypeItem(self, uuid, item):
        r = self.session.post(self.resolve('devicetype-delete'), data={"id" : uuid, "resourceId" : item})
        if r.status_code == 200:
            return True
        return False

    def createDeviceType(self, content):
        payload = {"fromCodeType" : "code", "create" : "Create", "content" : content}
        r = self.session.post(self.resolve("devicetype-create"), data=payload, allow_redirects=False)
        if r.status_code != 302:
            print "ERROR: Unable to create item"
            return None

        p = re.compile('.*/ide/device/editor/([a-f0-9\-]+)', re.MULTILINE|re.IGNORECASE|re.DOTALL)
        m = p.match(r.headers["Location"])

        return m.group(1)

    def deleteDeviceType(self, uuid):
        payload = {"id" : uuid, "_action_delete" : "Delete"}
        r = self.session.post(self.resolve('devicetype-destroy'), data=payload, allow_redirects=False)
        if r.status_code == 302:
            return True
        return False

    def downloadSmartAppItem(self, smartapp, details, uuid):
        return self.downloadItem("smartapp-download", smartapp, details, uuid)

    def downloadDeviceTypeItem(self, devicetype, details, uuid):
        return self.downloadItem("devicetype-download", devicetype, details, uuid)

    # Convenience, downloads an entire smartapp
    def downloadBundle(self, kind, uuid, dest):
        print "Downloading bundle..."
        if kind == STServer.TYPE_SA:
            data = self.getSmartAppDetails(uuid)
        elif kind == STServer.TYPE_DTH:
            data = self.getDeviceTypeDetails(uuid)
        else:
            print "ERROR: Unsupported type"
            return False

        try:
            os.makedirs(dest)
        except:
            pass
        for i in data["flat"]:
            sys.stdout.write("  Downloading " + i + ": ")
            if kind == STServer.TYPE_SA:
                content = self.downloadSmartAppItem(uuid, data["details"], i)
            elif kind == STServer.TYPE_DTH:
                content = self.downloadDeviceTypeItem(uuid, data["details"], i)
            if content is None:
                print "Failed"
            else:
                filename = dest + content["path"] + "/" + content["filename"]
                print "OK (%s)" % content["filename"]
                try:
                    os.makedirs(dest + content["path"])
                except:
                    pass
                with open(filename, "wb") as f:
                    f.write(content["data"])
        return True

    def downloadSmartApp(self, uuid, dest):
        return self.downloadBundle(self.TYPE_SA, uuid, dest)

    def downloadDeviceType(self, uuid, dest):
        return self.downloadBundle(self.TYPE_DTH, uuid, dest)

    def publishDeviceType(self, uuid):
        payload = {"id" : uuid, "scope" : "me"}
        r = self.session.post(self.resolve('devicetype-publish'), data=payload, allow_redirects=False)
        if r.status_code == 200:
            return True
        return False

    def publishSmartApp(self, uuid):
        payload = {"id" : uuid, "scope" : "me"}
        r = self.session.post(self.resolve('smartapp-publish'), data=payload, allow_redirects=False)
        if r.status_code == 200:
            return True
        return False
