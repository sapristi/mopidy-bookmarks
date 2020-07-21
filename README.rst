****************************
Mopidy-Bookmarks
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-Bookmarks
    :target: https://pypi.org/project/Mopidy-Bookmarks/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/circleci/build/gh/sapristi/mopidy-bookmarks
    :target: https://circleci.com/gh/sapristi/mopidy-bookmarks
    :alt: CircleCI build status

.. image:: https://img.shields.io/codecov/c/gh/sapristi/mopidy-bookmarks
    :target: https://codecov.io/gh/sapristi/mopidy-bookmarks
    :alt: Test coverage

Provides bookmarks functionalities to mopidy.

Bookmarks are playlist that can be synced with the current playback state, so that you can easily stop listening to some tracklist, listen to something else, and later resume at the position where you stopped. This is most usefull when listening to audiobooks.

This extension can only be used with a compatible mopidy client. For now, only `mopidy-mowecl`_ is compatible.

.. _mopidy-mowecl: https://mopidy.com/ext/mowecl/

Usage
=====

Bookmarks are playlists saved in a sqlite database.
When synchronising between a bookmark and playback state, the current track and current time will be saved periodically (every 0.5 second by default). As soon as the tracklist changes, or the `stop_sync` command is received, synchronisation will stop.
A bookmark can then be resumed with the `resume` command, replacing the tracklist with the bookmark tracks, and resuming playback from the saved state.

To create a bookmark, use the `Mopidy API`_, providing `bookmark:` as a `uri_scheme`. All the functions from the `Playlist controller API`_ are available.

.. _Mopidy API: https://docs.mopidy.com/en/latest/api/core/#mopidy.core.PlaylistsController.create
.. _Playlist controller API: https://docs.mopidy.com/en/latest/api/core/#playlists-controller

Access to the bookmarks API is provided by a websocket server, which works in exactly the same way as the mopidy websocket server. It can thus be used with the `Mopidy-js client`_ by connecting to the address `mopidy-host:port/bookmarks/ws`.

.. _Mopidy-js Client: https://github.com/mopidy/mopidy.js
  
The bookmarks API provides the following commands:

- `start_sync` : Start synchronising a given bookmark with the current tracklist.
- `resume` : Resumes playback from the given bookmark, and start syncing.
- `stop_sync` : Stop synchronisation between the current bookmark and playback status.
- `get_current_bookmark` : Get the current synchronising bookmark, if any.

See the `API section`_ for the API specification.

Moreover, the following event will be broadcasted to the connected websocket clients:

- `sync_status_update`: When sync status changes.

    The event payload is an object of the form `{bookmark: data}`, where `data` is the name of the bookmark being synchronised, or `null` if synchronisation has stopped.

.. _API section:

API
===

`start_sync(uri)`:   Starts syncing the given bookmark with the playback state.

    The tracklist must correspond to the tracks of the bookmark.

    *Parameters*
    
    uri : str
        The uri of the bookmark to resume

    *Returns*
    
    bool
        `True` if syncing started, else `False`
 
`resume(uri)`:   Resumes playback from a bookmark.

    Populates the tracklist with the tracks of the bookmark, resumes playback from
    the saved position and sync the bookmark with the current playback state (track and time).

    *Parameters*
    
    uri : str
        The uri of the bookmark to resume

    *Returns*
    
    bool
        `True` if a bookmark was found for the given uri, else `False`
 
`get_current_bookmark()`: Get the current synced bookmark if any.

    *Returns*
    
    mopidy.models.Ref or None
        A ref to the current bookmark if any, else None

`stop_sync()`:   Stop syncing the current bookmark.



Installation
============

Install by running::

    python3 -m pip install Mopidy-Bookmarks

Note that this extension is a dependency of `mopidy-mowecl`, so it will already be installed if you are using this client.

See https://mopidy.com/ext/bookmarks/ for alternative installation methods.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-Bookmarks to your Mopidy configuration file::

    [bookmarks]
    # TODO: Add example of extension config


Project resources
=================

- `Source code <https://github.com/sapristi/mopidy-bookmarks>`_
- `Issue tracker <https://github.com/sapristi/mopidy-bookmarks/issues>`_
- `Changelog <https://github.com/sapristi/mopidy-bookmarks/blob/master/CHANGELOG.rst>`_


Credits
=======

- Original author: `Mathias Millet <https://github.com/sapristi>`__
- Current maintainer: `Mathias Millet <https://github.com/sapristi>`__
- `Contributors <https://github.com/sapristi/mopidy-bookmarks/graphs/contributors>`_
