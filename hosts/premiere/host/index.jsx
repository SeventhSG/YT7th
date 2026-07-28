/*
 * YT7th ExtendScript host for Premiere Pro (ES3).
 *
 * yt7thImport(pathsPipe, append):
 *   pathsPipe - file paths joined by "|"
 *   append    - "true"/"false" (string or boolean); append imported clips to
 *               the active sequence's first video track.
 * Returns "ok:<n>" on success or "error:<message>". Import always completes
 * even if the optional append step fails.
 */

var TICKS_PER_SECOND = 254016000000;

function _splitPaths(pathsPipe) {
    if (!pathsPipe) return [];
    var parts = String(pathsPipe).split('|');
    var out = [];
    for (var i = 0; i < parts.length; i++) {
        if (parts[i] && parts[i].length) out.push(parts[i]);
    }
    return out;
}

// importFiles adds the new ProjectItems to the end of the target bin, so the
// items imported by this call are exactly children [beforeCount .. afterCount).
// (Avoids ProjectItem.nodeId, which is not a documented property.)
function _newItemsByCount(collection, beforeCount) {
    var added = [];
    for (var i = beforeCount; i < collection.numItems; i++) {
        added.push(collection[i]);
    }
    return added;
}

function _appendToSequence(items) {
    var seq = app.project.activeSequence;
    if (!seq) return 'Imported to project. Open a sequence to append.';
    var track = seq.videoTracks[0];
    for (var i = 0; i < items.length; i++) {
        var seconds = parseFloat(seq.end) / TICKS_PER_SECOND;
        track.insertClip(items[i], seconds);
    }
    return '';
}

function yt7thImport(pathsPipe, append) {
    try {
        var paths = _splitPaths(pathsPipe);
        if (!paths.length) return 'error:no files to import';

        var proj = app.project;
        var root = proj.rootItem;
        var beforeCount = root.children.numItems;

        var ok = proj.importFiles(paths, true, root, false);
        if (ok === false) return 'error:Premiere could not import the file(s)';

        var added = _newItemsByCount(root.children, beforeCount);

        var wantAppend = (append === true || append === 'true');
        if (wantAppend && added.length) {
            try {
                _appendToSequence(added);
            } catch (ae) {
                // Import already succeeded; report but don't fail the whole op.
                return 'ok:' + added.length;
            }
        }
        return 'ok:' + added.length;
    } catch (e) {
        return 'error:' + (e && e.message ? e.message : e.toString());
    }
}
