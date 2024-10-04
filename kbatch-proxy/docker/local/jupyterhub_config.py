c = get_config()  # noqa

c.JupyterHub.authenticator_class = "jupyterhub.auth.DummyAuthenticator"
c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.services = [
    {
        "name": "kbatch",
        "url": "http://kbatch-proxy:80/",
        "api_token": "super-secret",
    }
]

## The ip or hostname for proxies and spawners to use
#          for connecting to the Hub.
#
#          Use when the bind address (`hub_ip`) is 0.0.0.0, :: or otherwise different
#          from the connect address.
#
#          Default: when `hub_ip` is 0.0.0.0 or ::, use `socket.gethostname()`,
#  otherwise use `hub_ip`.
#
#          Note: Some spawners or proxy implementations might not support hostnames. Check your
#          spawner or proxy documentation to see if they have extra requirements.
#
#          .. versionadded:: 0.8
#  Default: ''
# c.JupyterHub.hub_connect_ip = ''

## The URL for connecting to the Hub. Spawners, services, and the proxy will use
#  this URL to talk to the Hub.
#
#  Only needs to be specified if the default hub URL is not connectable (e.g.
#  using a unix+http:// bind url).
#
#  .. seealso::
#      JupyterHub.hub_connect_ip
#      JupyterHub.hub_bind_url
#
#  .. versionadded:: 0.9
#  Default: ''
# c.JupyterHub.hub_connect_url = ''

## The ip address for the Hub process to *bind* to.
#
#          By default, the hub listens on localhost only. This address must be accessible from
#          the proxy and user servers. You may need to set this to a public ip or '' for all
#          interfaces if the proxy or user servers are in containers or on a different host.
#
#          See `hub_connect_ip` for cases where the bind and connect address should differ,
#          or `hub_bind_url` for setting the full bind URL.
#  Default: '127.0.0.1'
# c.JupyterHub.hub_ip = '127.0.0.1'

## The internal port for the Hub process.
#
#          This is the internal port of the hub itself. It should never be accessed directly.
#          See JupyterHub.port for the public port to use when accessing jupyterhub.
#          It is rare that this port should be set except in cases of port conflict.
#
#          See also `hub_ip` for the ip and `hub_bind_url` for setting the full
#  bind URL.
#  Default: 8081
# c.JupyterHub.hub_port = 8081

## The routing prefix for the Hub itself.
#
#  Override to send only a subset of traffic to the Hub. Default is to use the
#  Hub as the default route for all requests.
#
#  This is necessary for normal jupyterhub operation, as the Hub must receive
#  requests for e.g. `/user/:name` when the user's server is not running.
#
#  However, some deployments using only the JupyterHub API may want to handle
#  these events themselves, in which case they can register their own default
#  target with the proxy and set e.g. `hub_routespec = /hub/` to serve only the
#  hub's own pages, or even `/hub/api/` for api-only operation.
#
#  Note: hub_routespec must include the base_url, if any.
#
#  .. versionadded:: 1.4
#  Default: '/'
# c.JupyterHub.hub_routespec = '/'
