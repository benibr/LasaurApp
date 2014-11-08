# lasersaur.py - control a networked Lasersaur from python
# Copyright (c) 2011 Nortd Labs
# Open Source by the terms of the Gnu Public License (GPL3) or higher.
# ###
#
# This is a client implementation that connects to the LasaurApp
# control software on a Lasersaur. 
#
# This library is an example client for the Lasersaur net API.
#
# Usage:
# ------
# import time
# import lasersaur
#
# jobname = lasersaur.load_library('Lasersaur.lsa')
# if lasersaur.ready():
#   lasersaur.run(jobname)
# 
# while not lasersaur.ready():
#   print "%s% done!" % (lasersaur.progress())
#   time.sleep(1)
# 
# print "job done"
#

import os
import time
import json
import base64
import urllib
import urllib2


__author__  = 'Stefan Hechenberger <stefan@nortd.com>'




class Lasersaur(object):

    def __init__(self, host="lasersaur.local", port=80, user="laser", pass_="laser"):
        """Create a Lasersaur client object."""
        self.host = host
        self.port = port
        self.user = user
        self.pass_ = pass_
        self._first_request = True


    def _auth(self):
        # urllib2: enable auth
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        top_level_url = "http://%s:%s/" % (self.host, self.port)
        password_mgr.add_password(None, top_level_url, self.user, self.pass_)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener) # use auth for all urllib2.urlopen()


    def _request(self, url, postdict=None, ret=False):
        """Make a http request.

        Raises:
            urllib2.URLError: Host not reachable.
            urllib2.HTTPError: Web server responded with an error code.
        """
        if self._first_request:
            # lazily install authentication opener
            self._auth()
            self._first_request = False

        # TODO: url encode
        url = "http://%s:%s%s" % (self.host, self.port, url)

        if postdict:
            postdata = urllib.urlencode(postdict)
        else:
            postdata = None
        req = urllib2.Request(url, postdata)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            nomachine = "No machine."
            if e.code == 400 and nomachine in e.read():
                print "ERROR: %s" % nomachine
            raise e
        if ret:
            return json.loads(response.read())
                


    ### LOW-LEVEL

    def config(self):
        """Get config from machine."""
        return self._request('/config', ret=True)

    def status(self):
        """Get status report of machine.
        {
            "appver": 15.00,
            'firmver': 15.00,
            'ready': False,
            'paused': False,
            'serial': False
            'pos':[0.0, 0.0, 0.0],
            'stops': {},        # x1, x2, y1, y2, z1, z2
                                # requested, buffer, marker, data, command, parameter, transmission
            'info': {},         # door, chiller

            ### super
            'offset': [0.0, 0.0, 0.0],
            'feedrate': 0.0,
            'intensity': 0.0,
            'duration': 0.0,
            'pixelwidth': 0.0,
        }
        """
        return self._request('/status', ret=True)

    def homing(self):
        self._request('/homing')

    def feedrate(self, val):
        self._request('/feedrate/%.2f' % val)

    def intensity(self, val):
        self._request('/intensity/%.2f' % val)

    def relative(self):
        self._request('/relative')
        
    def absolute(self):
        self._request('/absolute')

    def move(self, x, y, z=0.0):
        self._request('/move/%.4f/%.4f/%.4f' % (x,y,z))

    def air_on(self):
        self._request('/air_on')

    def air_off(self):
        self._request('/air_off')

    def aux1_on(self):
        self._request('/aux1_on')

    def aux1_off(self):
        self._request('/aux1_off')

    def offset(self, x, y, z=0.0):
        self._request('/offset/%.4f/%.4f/%.4f' % (x,y,z))

    def clear_offset(self):
        self._request('/clear_offset')




    ### JOBS QUEUE


    def convert(self, job, tolerance=None, optimize=True):
        """Convert a job file.

        Args:
            job: Path to job file (lsa, svg, dxf, or gcode).
            optimize: Flag for optimizing path tolerances.
        """
        import jobimport # dependancy only when actually needed
        base, name = os.path.split(job)
        with open(job) as fp:
            job = fp.read()
        name, ext = os.path.splitext(name)
        if ext != '.lsa':
            if tolerance is None:
                job = jobimport.convert(job, optimize=optimize)
            else:
                job = jobimport.convert(job, tolerance=tolerance, optimize=optimize)
            job = json.dumps(job)
            outfile = os.path.join(base, "%s.conv.lsa" % (name))
            with open(outfile,'w') as fp:
                fp.write(job)
            print "INFO: job file written to: %s" % outfile
        else:
            print "WARN: already a .lsa file"



    def load(self, job, name=None, convert=True, optimize=True):
        """Load a job file.

        Args:
            job: Path to job file (lsa, svg, dxf, or gcode).
            name: Name the job. Defaults to file name.
                  If not unique gets a post-numeral.
            convert: Flag for converting/optimizing locally.
            optimize: Flag for optimizing path tolerances.

        Returns:
            Unique name give to the job. This is either name or 
            name_<numeral>.
        """
        name_f = os.path.basename(job)
        with open(job) as fp:
            job = fp.read()
        name_f, ext = os.path.splitext(name_f)
        if convert:
            import jobimport # dependancy only when actually needed
            job = jobimport.convert(job, optimize)
            job = json.dumps(job)
            if optimize:
                optimize = False
        if name is None:
            name = name_f
        # load
        load_request = {"job": job, "name":name, "optimize": optimize}
        load_request = json.dumps(load_request)
        return self._request('/load', postdict={'load_request':load_request}, ret=True)



    def loads(self, job, name="job", convert=True, optimize=True):
        """Load a job from string (as opposed to read from file).

        Args:
            job: Can be: lsa (native), svg, dxf, or gcode.
            name: Name the job. If not unique gets a post-numeral.
            convert: Flag for converting/optimizing locally.
            optimize: Flag for optimizing path tolerances.

        Returns:
            Unique name give to the job. This is either name or 
            name_<numeral>.
        """
        # convert locally
        if convert:
            import jobimport  # dependancy only when actually needed
            job = jobimport.convert(job, optimize)
            job = json.dumps(job)
            if optimize:
                optimize = False
        # load
        load_request = {"job": job, "name":name, "optimize": optimize}
        load_request = json.dumps(load_request)
        return self._request('/load', postdict={'load_request':load_request}, ret=True)



    def load_path(self, path, feedrate, intensity):
        """Create and load a job from list of polylines.
        boundary looks like this:
        [ [[x,y,z], ...], [[x,y,z], ...], ... ]
        and can be 2D or 3D.
        """
        job = {
            "vector":{
                "passes":[
                    {
                        "path":[0],
                        "feedrate":feedrate,
                        "intensity":intensity
                    }
                ],
                "paths":[
                    path
                ]
            }
        }
        return self.loads(json.dumps(job))

    def load_image(self, image, pos, size, feedrate=6000, intensity=50):
        """Create and load a raster engraving job.

        Args;
            image: image file path to PNG image
            pos: (x,y), position of top-left corner
            size: (width, height), dimensions of output
            feedrate: raster speed
            intensity: raster intensity
        """
        with open(image,'rb') as fp:
            img = fp.read()
        img_b64 = base64.encodestring(img).decode("utf8")
        job = {
            "raster":{
                "passes":[
                    {
                        "images": [0],
                        "feedrate": feedrate,
                        "intensity": intensity,
                    },
                ],
                "images":[
                    {
                        "pos": pos,
                        "size": size, 
                        "data": img_b64
                    }
                ]
            }
        }
        return self.loads(json.dumps(job))

    def listing(self, kind=None):
        """List all queue jobs by name."""
        if kind is None:
            jobs = self._request('/listing', ret=True)
        elif kind == 'starred':
            jobs = self._request('/listing/starred', ret=True)
        elif kind == 'unstarred':
            jobs = self._request('/listing/unstarred', ret=True)
        return jobs

    def get(self, jobname):
        """Get a queue job in .lsa format."""
        return self._request('/get/%s' % jobname, ret=True)

    def star(self, jobname):
        """Star a job."""
        self._request('/star/%s' % jobname)

    def unstar(self, jobname):
        """Unstar a job."""
        self._request('/unstar/%s' % jobname)

    def remove(self, jobname):
        """Delete a job."""
        self._request('/remove/%s' % jobname)

    def clear(self):
        """Clear job list (does not delete starred jobs)."""
        self._request('/clear')


    ### LIBRARY

    def listing_library(self):
        """List all library jobs by name."""
        return self._request('/listing_library', ret=True)

    def get_library(self, jobname):
        """Get a library job in .lsa format."""
        return self._request('/get_library/'+jobname, ret=True)

    def load_library(self, jobname):
        """Load a library job into the queue."""
        return self._request('/load_library/%s' % (jobname), ret=True)


    ### JOB EXECUTION

    def run(self, jobname, async=True):
        """Send job from queue to the machine."""
        self._request('/run/%s' % jobname)
        if not async:
            while not self.ready(cache=0):
                time.sleep(1)

    def progress(self):
        """Get percentage of job done."""
        return self._request('/progress', ret=True)

    def pause(self):
        """Pause a job gracefully."""
        self._request('/pause')

    def unpause(self):
        """Resume a paused job."""
        self._request('/unpause')

    def stop(self):
        """Halt machine immediately and purge job."""
        self._request('/stop')

    def unstop(self):
        """Recover machine from stop mode."""
        self._request('/unstop')


    ### MCU MANAGMENT

    def build(self, firmware_name=None):
        """Build firmware from firmware/src files."""
        if firmware_name:
            self._request('/build')
        else:
            self._request('/build/'+firmware_name)

    def flash(self, firmware_name=None):
        """Flash firmware to MCU."""
        if firmware_name:
            self._request('/flash')
        else:
            self._request('/flash/'+firmware_name)

    def reset(self):
        """Reset MCU"""
        self._request('/reset')




###########################################################################
### API ###################################################################
###########################################################################

lasersaur = Lasersaur()
### LOW-LEVEL
config = lasersaur.config
status = lasersaur.status
homing = lasersaur.homing
feedrate = lasersaur.feedrate
intensity = lasersaur.intensity
relative = lasersaur.relative
absolute = lasersaur.absolute
move = lasersaur.move
air_on = lasersaur.air_on
air_off = lasersaur.air_off
aux1_on = lasersaur.aux1_on
aux1_off = lasersaur.aux1_off
offset = lasersaur.offset
clear_offset = lasersaur.clear_offset
### JOBS QUEUE
convert = lasersaur.convert
load = lasersaur.load
loads = lasersaur.loads
load_path = lasersaur.load_path
load_image = lasersaur.load_image
listing = lasersaur.listing
get = lasersaur.get
star = lasersaur.star
unstar = lasersaur.unstar
remove = lasersaur.remove
clear = lasersaur.clear
### LIBRARY
listing_library = lasersaur.listing_library
get_library = lasersaur.get_library
load_library = lasersaur.load_library
### JOB EXECUTION
run = lasersaur.run
progress = lasersaur.progress
pause = lasersaur.pause
unpause = lasersaur.unpause
stop = lasersaur.stop
unstop = lasersaur.unstop
### MCU MANAGMENT
build = lasersaur.build
flash = lasersaur.flash
reset = lasersaur.reset


def set_host(host):
    """Set host. Call this before making first request."""
    lasersaur.host = host

def set_port(port):
    """Set user. Call this before making first request."""
    lasersaur.port = port

def set_user(user):
    """Set user. Call this before making first request."""
    lasersaur.user = user
    
def set_pass(pass_):
    """Set password. Call this before making first request."""
    lasersaur.pass_ = pass_




if __name__ == '__main__':
    jobname = lasersaur.load_library('Lasersaur.lsa')
    if lasersaur.ready():
      lasersaur.run(jobname)

    while not lasersaur.ready():
      print "%s done!" % (lasersaur.progress())
      time.sleep(1)

    print "job done"