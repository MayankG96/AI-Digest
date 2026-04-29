"""
formatter.py — Builds a polished HTML email from ranked AI news items.
Uses inline CSS only (Gmail strips <style> tags).
"""

from __future__ import annotations


def build_email_html(items: list[dict], date_str: str) -> str:
    """
    Build a complete HTML email string from ranked news items.

    Args:
        items:    List of 7 ranked dicts (rank, title, source, url, score,
                  summary, why_it_matters).
        date_str: Human-readable date string, e.g. "Monday, April 28, 2026".

    Returns:
        A complete HTML document as a string, suitable for sending via SMTP.
    """
    n = len(items)
    story_word = "story" if n == 1 else "stories"

    # ------------------------------------------------------------------ #
    # Build story cards
    # ------------------------------------------------------------------ #
    cards_html = ""
    for idx, item in enumerate(items):
        rank = item.get("rank", idx + 1)
        title = _esc(item.get("title", "Untitled"))
        source = _esc(item.get("source", "Unknown"))
        url = _esc(item.get("url", "#"))
        score = item.get("score", "")
        summary = _esc(item.get("summary", ""))
        why = _esc(item.get("why_it_matters", ""))

        num_label = str(rank).zfill(2)
        score_badge = (
            f'<span style="background:#1a56ff;color:#fff;font-size:11px;'
            f'font-family:\'SF Mono\',\'Fira Code\',monospace;font-weight:700;'
            f'padding:3px 8px;border-radius:4px;white-space:nowrap;">⬆ {score}</span>'
            if score
            else ""
        )

        divider = (
            '<hr style="border:none;border-top:1px solid #e8e8e8;margin:28px 0 0 0;">'
            if idx < n - 1
            else ""
        )

        cards_html += f"""
        <!-- Story {rank} -->
        <tr>
          <td style="padding:28px 40px 0 40px;">
            <!-- Header row: number + title + score -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="width:32px;vertical-align:top;padding-top:2px;">
                  <span style="font-family:'SF Mono','Fira Code',monospace;
                               font-size:11px;color:#b0b0b0;font-weight:600;
                               letter-spacing:0.04em;">{num_label}</span>
                </td>
                <td style="vertical-align:top;padding-right:12px;">
                  <a href="{url}"
                     style="font-size:17px;font-weight:700;color:#0a0a0f;
                            text-decoration:none;line-height:1.35;display:block;">
                    {title}
                  </a>
                  <div style="margin-top:4px;">
                    <span style="font-family:'SF Mono','Fira Code',monospace;
                                 font-size:10px;color:#888;text-transform:uppercase;
                                 letter-spacing:0.08em;">{source}</span>
                  </div>
                </td>
                <td style="vertical-align:top;white-space:nowrap;">
                  {score_badge}
                </td>
              </tr>
            </table>
            <!-- Summary -->
            <p style="margin:12px 0 0 32px;font-size:14px;color:#555;
                      line-height:1.65;">{summary}</p>
            <!-- Why it matters -->
            <div style="margin:14px 0 0 32px;padding:12px 16px;
                        background:#f5f5f7;border-left:3px solid #0a0a0f;
                        border-radius:0 4px 4px 0;">
              <div style="font-family:'SF Mono','Fira Code',monospace;
                          font-size:10px;color:#0a0a0f;text-transform:uppercase;
                          letter-spacing:0.1em;font-weight:700;margin-bottom:6px;">
                Why This Matters
              </div>
              <p style="margin:0;font-size:13px;color:#444;line-height:1.65;">{why}</p>
            </div>
            {divider}
          </td>
        </tr>
"""

    # ------------------------------------------------------------------ #
    # Full email skeleton
    # ------------------------------------------------------------------ #
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Daily AI Digest — {_esc(date_str)}</title>
</head>
<body style="margin:0;padding:0;background:#f0f0f2;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f0f0f2;padding:32px 0;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background:#ffffff;
                      border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 16px rgba(0,0,0,0.08);">

          <!-- ============================================================ -->
          <!-- HEADER                                                        -->
          <!-- ============================================================ -->
          <tr>
            <td style="background:#0a0a0f;padding:36px 40px 32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <div style="font-size:22px;font-weight:800;color:#ffffff;
                                letter-spacing:-0.02em;line-height:1.2;">
                      Your Daily AI Digest
                    </div>
                    <div style="margin-top:6px;font-size:13px;color:#8a8a9a;
                                letter-spacing:0.02em;">
                      {_esc(date_str)}
                    </div>
                  </td>
                  <td align="right" style="vertical-align:top;">
                    <span style="background:#1a56ff;color:#fff;font-size:12px;
                                 font-weight:700;padding:5px 12px;border-radius:20px;
                                 white-space:nowrap;">{n}&nbsp;{story_word}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ============================================================ -->
          <!-- INTRO                                                         -->
          <!-- ============================================================ -->
          <tr>
            <td style="padding:24px 40px 8px 40px;border-bottom:1px solid #e8e8e8;">
              <p style="margin:0;font-size:14px;color:#666;line-height:1.6;
                        font-style:italic;">
                Good morning. Here are today's {n} most significant stories ranked
                by novelty and impact.
              </p>
            </td>
          </tr>

          <!-- ============================================================ -->
          <!-- STORIES                                                       -->
          <!-- ============================================================ -->
          {cards_html}

          <!-- ============================================================ -->
          <!-- FOOTER                                                        -->
          <!-- ============================================================ -->
          <tr>
            <td style="background:#f7f7f9;padding:20px 40px;
                       border-top:1px solid #e8e8e8;">
              <p style="margin:0;font-size:11px;color:#aaa;text-align:center;
                        line-height:1.6;">
                Generated daily at 6:00&nbsp;AM&nbsp;PST&nbsp;·&nbsp;
                Sources: HN, ArXiv, VentureBeat, TechCrunch, The Batch, Import AI
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
  <!-- /Outer wrapper -->

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Minimal HTML escaping for safe inline insertion."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
