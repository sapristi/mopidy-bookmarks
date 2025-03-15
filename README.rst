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

Inner design and operation
==========================

Bookmarks are exposed as regular mopidy playlists, under the `bookmark:` uri.

A websocket interface gives additional control:

- start syncing the current tracklist with a bookmark, i.e. store current track and time along with the playlist.
- resume a given bookmark (i.e. restore tracklist and start playing).
- stop the syncing.


When synchronising between a bookmark and playback state, the current track and current time will be saved periodically (every 0.5 second by default). As soon as the tracklist changes, or the ``stop_sync`` command is received, synchronisation will stop.

All the data is stored in a sqlite database.

Usage
=====

Access to the bookmarks API is provided by a websocket server, which works in exactly the same way as the mopidy websocket server. It can thus be used with the `Mopidy-js client`_ by connecting to the address ``mopidy-host:port/bookmarks/ws``.



1. Create the clients

    .. code-block:: javascript

        const mopidyClient = new Mopidy({
          webSocketUrl: "ws://localhost:6680/mopidy/ws/",
        });
        const bookmarksClient = new Mopidy({
          webSocketUrl: "ws://localhost:6680/bookmarks/ws/",
        });

2. To create a bookmark, simply create a new playlist (here from current tracklist):

    .. code-block:: javascript

        const BookmarkName = "my bookmark";
        const tracks = await mopidyClient.tracklist.getTracks();
        const BMPlaylist = await mopidyClient.playlists.create({
            name: BookmarkName,
            uri_scheme: "bookmark",
          })
        BMPlaylist.tracks = tracks;
        await mopidyClient.play.save({playlist: BMPlaylist})

3. You can then start syncronisation:

    .. code-block:: javascript

        bookmarksClient.startSync({uri: BMPlaylist.uri })

3. Stop synchronisation manually at any time:

    .. code-block:: javascript

        bookmarksClient.stopSync()

5. And restore tracklist and playback state with the resume command:

    .. code-block:: javascript

        bookmarksClient.resume({uri: BMPlaylist.uri })



6. Finally, you can react to change in synchronisation status with the following:
    .. code-block:: javascript

      bookmarksClient.on("event:syncStatusUpdate", (newStatus) => ... )

.. _Mopidy-js Client: https://github.com/mopidy/mopidy.js


API
===

Commands
--------

``start_sync(uri)``:   Starts syncing the given bookmark with the playback state.

    The tracklist must correspond to the tracks of the bookmark.

    *Parameters*
    
    uri : str
        The uri of the bookmark to resume

    *Returns*
    
    bool
        ``True`` if syncing started, else ``False``
 
``resume(uri)``:   Resumes playback from a bookmark.

    Populates the tracklist with the tracks of the bookmark, resumes playback from
    the saved position and sync the bookmark with the current playback state (track and time).

    *Parameters*
    
    uri : str
        The uri of the bookmark to resume

    *Returns*
    
    bool
        ``True`` if a bookmark was found for the given uri, else ``False``
 
``get_current_bookmark()``: Get the current synced bookmark if any.

    *Returns*
    
    mopidy.models.Ref or None
        A ref to the current bookmark if any, else None

``stop_sync()``:   Stop syncing the current bookmark.

Events
------

``sync_status_update``: When sync status changes.

    The event payload is an object of the form ``{bookmark: data}``, where ``data`` is the name of the bookmark being synchronised, or ``null`` if synchronisation has stopped.



Installation
============

Install by running::

    python3 -m pip install Mopidy-Bookmarks

Note that this extension is a dependency of ``mopidy-mowecl``, so it will already be installed if you are using this client.


Configuration
=============

Mopidy-Bookmarks provides the following configuration keys (and their default values). ::

      [bookmarks]
      enabled = true

      # sync period, in milliseconds
      sync_period = 500

      # set this to false to enable limits defined below
      # (usefull if mopidy listens on a public network e.g.)
      disable_limits = true
      # max number of bookmarks
      max_bookmarks = 100
      # max size of data for one bookmark
      max_bookmark_length = 100000

      # max number of items in store
      max_store_items = 10
      # max store item length
      max_store_item_length = 1000

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
