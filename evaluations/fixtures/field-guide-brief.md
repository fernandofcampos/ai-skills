# Field guide index distribution proposal
Revision FG-7, 2026-11-12. Maintainer draft for discussion.

Rangers search the field guide on tablets that can spend several days offline.
The approved product requirement in this brief is that an interrupted catalog
update must leave the previous complete, searchable edition available.

Engineering proposes publishing one immutable SQLite search index per edition.
The tablet downloads a candidate beside the current index, verifies the manifest
digest and format version, and switches editions only after verification.
This would also require free space for both editions during an update.

Sending incremental edits uses less bandwidth, but applying part of an edition
could expose mixed results unless the tablet implements atomic batches and a
recovery log. Offering live server-side search would simplify the client, but
would make search unavailable offline.

Reopen the decision if field measurements show that two editions do not fit on
supported tablets or that full downloads routinely miss the synchronization window.
The fleet has not yet measured free space or update duration. No team has approved
the technical proposal. No implementation, deployment, or decision owner was supplied.
