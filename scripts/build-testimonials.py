#!/usr/bin/env python3
"""Write client testimonials into the pages that show them.

Each testimonial is defined once, in TESTIMONIALS below. A page opts in by
carrying a pair of marker comments where the quotes should sit, listing the
ones it wants in the order it wants them shown:

    <!-- testimonial: demarku-style, demarku-dialogue -->
    <!-- /testimonial -->

Two or more keys make a carousel: one quote showing at a time, with dots
underneath that site.js wires up. It is a horizontal scroll-snap strip, so it
swipes on a phone and still scrolls with scripting off. One key makes a single
quote with no dots.

Everything between the markers is regenerated on each run, so edit the quote
here, never in the page. The output is plain HTML rather than something site.js
injects, which keeps the quotes visible to search engines and to readers with
scripting off.

Only publish words the client actually wrote, or a shortened version they have
approved, and only once they have agreed to be named.

Usage:
    python scripts/build-testimonials.py           # rewrite every marked slot
    python scripts/build-testimonials.py --check   # exit 1 if any page is stale
    python scripts/build-testimonials.py --list    # show which page uses which

Run it from the repository root.
"""

import argparse
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- Testimonials ----------------------------------------------------------
# `quote` is plain text: it is HTML-escaped on the way out, so write
# apostrophes and ampersands normally. Separate paragraphs with a blank line.
# `role` and `link` are optional.

TESTIMONIALS = {
    "demarku-style": dict(
        quote="The most useful response I've had on this book. What struck me "
              "most was that you separated where the stripped-back style is "
              "doing its job from the few places where it leaves the reader "
              "guessing. Nobody else made that distinction.",
        name="Armando Demarku",
        role="Author, Demarku Publishing",
        link="https://www.demarkupublishing.com/",
    ),
    "demarku-dialogue": dict(
        quote="I've received feedback on the same chapter from several "
              "editors, and yours has been the most useful. Others asked for "
              "more dialogue tags in general terms; you pointed to the exact "
              "places where a reader loses track of who is speaking.",
        name="Armando Demarku",
        role="Author, Demarku Publishing",
        link="https://www.demarkupublishing.com/",
    ),
}

MARKER = re.compile(
    r"(?P<indent>[ \t]*)<!-- testimonial: (?P<keys>[\w-]+(?:\s*,\s*[\w-]+)*) -->\n"
    r".*?"
    r"[ \t]*<!-- /testimonial -->",
    re.DOTALL,
)


def render_one(key):
    """One quote as a list of unindented lines."""
    t = TESTIMONIALS[key]
    paras = [p.strip() for p in t["quote"].split("\n\n") if p.strip()]
    role = t.get("role", "")
    if t.get("link") and role:
        # Link the organisation part of the role, i.e. the text after the comma.
        head, _, org = role.rpartition(", ")
        org_html = '<a href="{}" rel="noopener">{}</a>'.format(
            html.escape(t["link"]), html.escape(org or role))
        role_html = (html.escape(head) + ", " + org_html) if head else org_html
    else:
        role_html = html.escape(role)

    lines = ['<figure class="testimonial">', "  <blockquote>"]
    lines += ["    <p>{}</p>".format(html.escape(p, quote=False)) for p in paras]
    lines += ["  </blockquote>", "  <figcaption>"]
    lines.append('    <span class="testimonial-name">{}</span>'.format(html.escape(t["name"])))
    if role_html:
        lines.append('    <span class="testimonial-role">{}</span>'.format(role_html))
    lines += ["  </figcaption>", "</figure>"]
    return lines


def render(keys, indent):
    n = len(keys)
    if n == 1:
        lines = ['<div class="testimonials reveal">']
        lines += ["  " + l for l in render_one(keys[0])]
        lines.append("</div>")
    else:
        lines = ['<div class="testimonials reveal" role="region" '
                 'aria-roledescription="carousel" aria-label="What clients say">',
                 '  <div class="testimonial-track" tabindex="0">']
        for i, key in enumerate(keys):
            lines.append('    <div class="testimonial-slide" id="{}-{}" role="group" '
                         'aria-roledescription="slide" aria-label="{} of {}">'.format(key, i + 1, i + 1, n))
            lines += ["      " + l for l in render_one(key)]
            lines.append("    </div>")
        lines.append("  </div>")
        lines.append('  <div class="testimonial-dots">')
        for i, key in enumerate(keys):
            lines.append('    <button type="button" class="testimonial-dot" aria-controls="{}-{}" '
                         'aria-label="Show testimonial {} of {}"{}></button>'.format(
                             key, i + 1, i + 1, n, ' aria-current="true"' if i == 0 else ""))
        lines += ["  </div>", "</div>"]

    body = "\n".join(indent + line for line in lines)
    return "{0}<!-- testimonial: {1} -->\n{2}\n{0}<!-- /testimonial -->".format(
        indent, ", ".join(keys), body)


def process(path, write):
    # The pages are checked out with CRLF endings; read_text folds them to \n,
    # so remember which the file used and write it back the same way.
    eol = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
    text = path.read_text(encoding="utf-8")
    used = []

    def sub(m):
        keys = [k.strip() for k in m.group("keys").split(",")]
        for key in keys:
            if key not in TESTIMONIALS:
                sys.exit("{}: unknown testimonial '{}'".format(path.name, key))
        used.extend(keys)
        return render(keys, m.group("indent"))

    new = MARKER.sub(sub, text)
    changed = new != text
    if changed and write:
        path.write_text(new, encoding="utf-8", newline=eol)
    return used, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    stale = []
    for path in sorted(ROOT.glob("*.html")):
        used, changed = process(path, write=not (args.check or args.list))
        if args.list and used:
            print("{}: {}".format(path.name, ", ".join(used)))
        if changed:
            stale.append(path.name)

    if args.check:
        if stale:
            print("Out of date: " + ", ".join(stale))
            sys.exit(1)
        print("All testimonials up to date.")
    elif not args.list:
        print("Updated: " + (", ".join(stale) if stale else "nothing to change"))


if __name__ == "__main__":
    main()
