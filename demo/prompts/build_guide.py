#!/usr/bin/env python3
"""Build demo/higgsfield-guide.html: a step-by-step guide for making every asset by hand
on the Higgsfield website, with all prompts from prompts.json and copy buttons.

Usage: python3 demo/prompts/build_guide.py
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "higgsfield-guide.html"
D = json.loads((ROOT / "prompts.json").read_text())
CHARS = {c["key"]: c for c in D["characters"]}
CLIPS = {c["id"]: c for c in D["clips"]}
E = html.escape

_n = 0


def prompt_box(text, label="Copy"):
    global _n
    _n += 1
    return (f'<div class="prompt"><pre id="p{_n}">{E(text)}</pre>'
            f'<button type="button" class="copy" data-target="p{_n}">{E(label)}</button></div>')


def check(id_, text):
    return f'<label class="tick"><input type="checkbox" id="ck-{id_}"> <span>{text}</span></label>'


def character(c, optional=False):
    k = c["key"]
    imgs = c["images"]
    note = '<p class="note">Only needed for the extra clips A7 and A8. Skip it for now.</p>' if optional else ""
    return f"""
<details class="item" id="char-{k}">
  <summary><span class="tag">{E(c['tag'])}</span> <span class="what">{E(c['name'])}</span>
    <span class="files">{k}_sheet.png · {k}_front.png · {k}_back.png</span></summary>
  {note}
  <h4>1 · Reference sheet <small>aspect 16:9 · no reference image</small></h4>
  {prompt_box(imgs['sheet'])}
  <p class="save">Save as <code>{k}_sheet.png</code></p>
  <h4>2 · Front photo <small>aspect 3:4 · attach {k}_sheet.png as the reference image</small></h4>
  {prompt_box(imgs['front'])}
  <p class="save">Save as <code>{k}_front.png</code></p>
  <h4>3 · Back photo <small>aspect 3:4 · attach {k}_sheet.png as the reference image</small></h4>
  {prompt_box(imgs['back'])}
  <p class="save">Save as <code>{k}_back.png</code></p>
  {check('char-' + k, 'All three pictures show the same person in the same clothes')}
</details>"""


def clip(cid):
    c = CLIPS[cid]
    cast = [CHARS[k] for k in c["cast"]]
    tagged = [x for x in cast if x.get("images")]
    folder = "case-A" if c["case"] == "A" else "case-B"
    if tagged:
        elements = ", ".join(f'<span class="tag">{E(x["tag"])}</span>' for x in tagged)
        refs = ", ".join(f'<code>{x["key"]}_front.png</code>' for x in tagged)
        options = f"""
  <h4>Way 1 · With Elements <small>recommended</small></h4>
  <p>Add the Elements {elements} to the generation, then paste:</p>
  {prompt_box(c['prompt_tags'])}
  <h4>Way 2 · Without Elements <small>Kling 3.0 Omni / reference images</small></h4>
  <p>Attach these reference images in this order: {refs}. Then paste:</p>
  {prompt_box(c['prompt_full'])}"""
    else:
        options = f"""
  <p>No Elements: these strangers are described in full inside the prompt. Don't attach any picture.</p>
  {prompt_box(c['prompt_full'])}"""
    return f"""
<details class="item" id="clip-{cid}">
  <summary><span class="cid">{cid}</span> <span class="what">{E(c['title'])}</span>
    <span class="files">camera {E(c['cam'])} · clock {E(c['clock'])}</span></summary>
  <p class="why">{E(c['why'])}</p>
  {options}
  <p class="save">Save as <code>{cid}.mp4</code> → upload to <code>demo/raw/{folder}/</code></p>
  {check('clip-' + cid, f'{cid} passed the checklist and is uploaded')}
</details>"""


main_chars = [c for c in D["characters"] if c.get("images") and c["key"] != "GUARD"]
chars_a = "".join(character(c) for c in main_chars if c["case"] == "A")
chars_b = "".join(character(c) for c in main_chars if c["case"] == "B")
guard = character(CHARS["GUARD"], optional=True)

page = f"""<title>Higgsfield Production Guide</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Public+Sans:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column, like a production call sheet; each step is a numbered block,
   every prompt sits in a mono box with its copy button. Accent = CCTV timestamp amber. */
:root {{
  --bg: #f3f4f6; --panel: #ffffff; --ink: #1b2330; --muted: #5b6577; --line: #d9dde4;
  --accent: #b86e00; --accent-soft: #fff3df; --code: #eef0f4; --ok: #2f7d4f; --warn: #a33a2b;
  --f-display: "Barlow Condensed", "Arial Narrow", sans-serif;
  --f-body: "Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --f-mono: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #12161d; --panel: #1a2029; --ink: #e5e9f0; --muted: #98a2b3; --line: #2c3440;
  --accent: #f0a63a; --accent-soft: #2a2215; --code: #0e1218; --ok: #6cc391; --warn: #f08a7a; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #12161d; --panel: #1a2029; --ink: #e5e9f0; --muted: #98a2b3; --line: #2c3440;
  --accent: #f0a63a; --accent-soft: #2a2215; --code: #0e1218; --ok: #6cc391; --warn: #f08a7a; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font: 16px/1.6 var(--f-body); }}
.wrap {{ max-width: 52rem; margin: 0 auto; padding-inline: 16px; padding-block: 2rem 4rem; }}
header .eyebrow {{ font: 600 .8rem var(--f-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }}
h1 {{ font: 700 clamp(2.2rem, 6vw, 3.4rem)/1 var(--f-display); letter-spacing: .01em; margin: .3rem 0 .8rem; text-wrap: balance; }}
h2 {{ font: 700 1.75rem/1.1 var(--f-display); margin: 0; text-wrap: balance; }}
h3 {{ font: 600 1.15rem/1.2 var(--f-display); letter-spacing: .02em; text-transform: uppercase; color: var(--muted); margin: 1.6rem 0 .5rem; }}
h4 {{ font: 600 1rem var(--f-body); margin: 1.2rem 0 .4rem; }}
h4 small {{ font: 400 .8rem var(--f-mono); color: var(--muted); margin-left: .4rem; }}
p, li {{ max-width: 65ch; }}
a {{ color: var(--accent); }}
code {{ font: .85em var(--f-mono); background: var(--code); padding: .1em .35em; border-radius: 3px; overflow-wrap: anywhere; }}
.lead {{ font-size: 1.1rem; color: var(--muted); }}
.steps {{ display: grid; gap: 1.25rem; margin-top: 2rem; }}
.step {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1.25rem 1.25rem 1.5rem; min-width: 0; }}
.step-head {{ display: flex; gap: .9rem; align-items: baseline; flex-wrap: wrap; }}
.num {{ font: 700 1rem var(--f-mono); color: var(--accent); }}
.meta {{ font: .8rem var(--f-mono); color: var(--muted); }}
.stop {{ border-left: 4px solid var(--warn); background: var(--accent-soft); padding: .8rem 1rem; border-radius: 0 4px 4px 0; margin-top: 1rem; }}
.stop strong {{ color: var(--warn); }}
.settings {{ display: grid; grid-template-columns: max-content 1fr; gap: .3rem 1rem; margin: .6rem 0; font-size: .95rem; }}
.settings dt {{ font: 500 .85rem var(--f-mono); color: var(--muted); padding-top: .1rem; }}
.settings dd {{ margin: 0; min-width: 0; }}
.item {{ border-top: 1px solid var(--line); }}
.item:last-of-type {{ border-bottom: 1px solid var(--line); }}
.item summary {{ cursor: pointer; padding: .75rem 0; display: flex; flex-wrap: wrap; gap: .3rem .7rem; align-items: baseline; }}
.item summary:focus-visible, .copy:focus-visible, .tick input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.item[open] summary {{ color: var(--accent); }}
.what {{ font-weight: 600; }}
.files {{ font: .78rem var(--f-mono); color: var(--muted); overflow-wrap: anywhere; }}
.tag, .cid {{ font: 500 .85rem var(--f-mono); background: var(--accent-soft); color: var(--accent); padding: .05em .4em; border-radius: 3px; }}
.prompt {{ position: relative; margin: .3rem 0 .5rem; }}
.prompt pre {{ margin: 0; background: var(--code); border: 1px solid var(--line); border-radius: 4px; padding: .8rem 1rem 2.6rem;
  font: .82rem/1.55 var(--f-mono); white-space: pre-wrap; overflow-wrap: anywhere; max-height: 20rem; overflow: auto; }}
.copy {{ position: absolute; right: .5rem; bottom: .5rem; font: 600 .8rem var(--f-body); background: var(--accent); color: var(--panel);
  border: 0; border-radius: 4px; padding: .35rem .8rem; cursor: pointer; }}
.copy.done {{ background: var(--ok); }}
.save {{ font-size: .9rem; color: var(--muted); margin: .2rem 0; }}
.why, .note {{ color: var(--muted); font-style: italic; }}
.tick {{ display: flex; gap: .5rem; align-items: center; margin: 1rem 0 .8rem; font-weight: 600; }}
.tick input {{ width: 1.1rem; height: 1.1rem; accent-color: var(--ok); }}
.check li {{ margin: .2rem 0; }}
.foot {{ margin-top: 2.5rem; font-size: .85rem; color: var(--muted); }}
@media (max-width: 30rem) {{ .settings {{ grid-template-columns: 1fr; }} .settings dd {{ margin-bottom: .4rem; }} }}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">Lost &amp; Found · asset production</div>
  <h1>Making the pictures and videos on Higgsfield</h1>
  <p class="lead">Every prompt you need, in the order to use it. Open a step, press <b>Copy</b>, paste it into Higgsfield.
  Tick the boxes as you go; they're remembered in this browser.</p>
</header>

<div class="steps">

<section class="step" id="s0">
  <div class="step-head"><span class="num">STEP 0</span><h2>Before you start</h2></div>
  <ul>
    <li>Log in at <a href="https://higgsfield.ai" target="_blank" rel="noopener">higgsfield.ai</a> and check your credits (top right). Pictures are cheap; each 15-second video costs about 30 credits at 720p.</li>
    <li>Make a folder on your computer called <code>lost-and-found</code> and save every file there with the exact name this page gives. The names matter: the system reads the camera and clip from them.</li>
    <li>Higgsfield changes its menus often. If a button has a slightly different name than here, look for the closest match.</li>
  </ul>
</section>

<section class="step" id="s1">
  <div class="step-head"><span class="num">STEP 1</span><h2>Character pictures</h2><span class="meta">6 characters × 3 pictures · image credits only</span></div>
  <p>Go to <b>Image</b> and pick <b>Nano Banana Pro</b> (if you don't have it, use <b>Soul</b>). For each character, make the three pictures in this order:</p>
  <ol>
    <li><b>Reference sheet</b>: aspect ratio <b>16:9</b>, no reference image. Generate 2–4 versions and keep the best one.</li>
    <li><b>Front photo</b>: aspect ratio <b>3:4</b>. Upload the sheet you just saved as the <b>reference image</b>, so it's the same person.</li>
    <li><b>Back photo</b>: same as the front, with the sheet as the reference image.</li>
  </ol>
  <p>Redo a picture if the clothes colour is wrong, there's text or a logo, or the front/back don't look like the sheet.</p>
  <h3>Case A family</h3>
  {chars_a}
  <h3>Case B family</h3>
  {chars_b}
  <h3>Optional</h3>
  {guard}
</section>

<section class="step" id="s2">
  <div class="step-head"><span class="num">STEP 2</span><h2>Turn each character into an Element</h2><span class="meta">free</span></div>
  <p>An Element keeps a person looking the same in every video. Go to <b>Video</b>, pick <b>Kling 3.0</b>, and open <b>Elements</b> (the <b>@</b> / element picker next to the prompt).</p>
  <ol>
    <li>Create a new Element (character).</li>
    <li>Upload the character's three pictures: sheet, front, back.</li>
    <li>Name it <b>exactly</b> like the tag, without spaces: <span class="tag">@FatherA</span> <span class="tag">@MotherA</span> <span class="tag">@BoyA</span> <span class="tag">@FatherB</span> <span class="tag">@MotherB</span> <span class="tag">@GirlB</span>. The video prompts use these names.</li>
  </ol>
  <p>If your plan has no Elements, skip this step and use <b>Way 2</b> in each clip below (the full description + the front photos as reference images, on <b>Kling 3.0 Omni</b>).</p>
  {check('elements', 'All 6 Elements created and named with the tags')}
</section>

<section class="step" id="s3">
  <div class="step-head"><span class="num">STEP 3</span><h2>The first two videos: A1 and A3</h2><span class="meta">2 videos</span></div>
  <p>Only these two first. They test whether CreativAI can find the family and the separation moment before you spend more credits.</p>
  <dl class="settings">
    <dt>Model</dt><dd>Kling 3.0 (Way 1) or Kling 3.0 Omni (Way 2)</dd>
    <dt>Aspect ratio</dt><dd>16:9</dd>
    <dt>Duration</dt><dd>15 s</dd>
    <dt>Resolution</dt><dd>720p (it's security footage; cheaper)</dd>
    <dt>Audio / sound</dt><dd>Off</dd>
    <dt>Multi-shot</dt><dd>Off (one fixed camera, no cuts)</dd>
    <dt>Negative prompt</dt><dd>If there's a field for it, paste this:</dd>
  </dl>
  {prompt_box(D['negative'], 'Copy negative prompt')}
  {clip('A1')}
  {clip('A3')}
  <div class="stop"><strong>Stop here.</strong> Upload A1.mp4 and A3.mp4 (Step 5) and tell me. I run the CreativAI test on them first.</div>
</section>

<section class="step" id="s4">
  <div class="step-head"><span class="num">STEP 4</span><h2>Check every clip before you keep it</h2></div>
  <ul class="check">
    <li>The camera <b>doesn't move</b>: no pan, zoom or shake.</li>
    <li>Clothes <b>keep the same colours</b> for the whole clip and match the pictures.</li>
    <li>The <b>key moment happens</b> (in A3 the boy really walks out of the store; in A6 the boy never leaves the table).</li>
    <li>No text, logo or watermark in the picture.</li>
    <li>Nothing grotesque (melting faces, extra arms). Small flaws are fine.</li>
  </ul>
  <p>If a clip fails, regenerate it once. We have 3 spare videos in the budget of 15.</p>
</section>

<section class="step" id="s5">
  <div class="step-head"><span class="num">STEP 5</span><h2>Send me the files</h2></div>
  <ol>
    <li>Download the video from Higgsfield and rename it, for example <code>A1.mp4</code>.</li>
    <li>Open the repo on GitHub: <a href="https://github.com/sahliadem0106/newnew/tree/claude/admiring-maxwell-ssqdjn" target="_blank" rel="noopener">sahliadem0106/newnew</a>, branch <code>claude/admiring-maxwell-ssqdjn</code>.</li>
    <li>Click <b>Add file → Upload files</b>. In the file name box at the top, type the folder first: <code>demo/raw/case-A/</code> (for pictures: <code>demo/assets/characters/</code>). Drop the files in and press <b>Commit changes</b>.</li>
    <li>Tell me in the chat which files you uploaded.</li>
  </ol>
  <p>Simpler alternative: attach the files directly in the chat with me.</p>
</section>

<section class="step" id="s6">
  <div class="step-head"><span class="num">STEP 6</span><h2>The rest of Case A</h2><span class="meta">4 videos · after my OK</span></div>
  <p>Same settings as Step 3.</p>
  {clip('A2')}{clip('A4')}{clip('A5')}{clip('A6')}
</section>

<section class="step" id="s7">
  <div class="step-head"><span class="num">STEP 7</span><h2>Case B, the blind test</h2><span class="meta">6 videos</span></div>
  <p>Same settings. Upload to <code>demo/raw/case-B/</code>. This case is kept sealed: the system is tested on it only once, after the code is frozen, so don't run anything on these clips yourself.</p>
  {clip('B1')}{clip('B2')}{clip('B3')}{clip('B4')}{clip('B5')}{clip('B6')}
</section>

<section class="step" id="s8">
  <div class="step-head"><span class="num">STEP 8</span><h2>Extras, only if spares are left</h2><span class="meta">for the demo video</span></div>
  <p>These need the guard (make the optional guard pictures in Step 1 and an Element named <span class="tag">@Guard</span>).</p>
  {clip('A7')}{clip('A8')}
</section>

</div>
<p class="foot">Built from <code>demo/prompts/prompts.json</code> by <code>demo/prompts/build_guide.py</code>. To change a prompt, edit <code>build_prompts.py</code>, then rebuild both.</p>
</div>

<script>
document.querySelectorAll('.copy').forEach(function (b) {{
  b.addEventListener('click', function () {{
    var pre = document.getElementById(b.dataset.target);
    var done = function () {{ var t = b.textContent; b.textContent = 'Copied'; b.classList.add('done');
      setTimeout(function () {{ b.textContent = t; b.classList.remove('done'); }}, 1500); }};
    var select = function () {{ var r = document.createRange(); r.selectNodeContents(pre);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Press Ctrl+C'; }};
    try {{ navigator.clipboard.writeText(pre.textContent).then(done, select); }} catch (e) {{ select(); }}
  }});
}});
document.querySelectorAll('.tick input').forEach(function (cb) {{
  try {{ cb.checked = localStorage.getItem(cb.id) === '1'; }} catch (e) {{}}
  cb.addEventListener('change', function () {{ try {{ localStorage.setItem(cb.id, cb.checked ? '1' : '0'); }} catch (e) {{}} }});
}});
</script>
"""

OUT.write_text(page)
print(f"wrote {OUT} ({len(page) // 1024} KB, {_n} prompts)")
