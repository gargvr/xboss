/*
 collect_profile.js: export your own X posts + profile facts as JSON, locally.

 How to use (takes ~30 seconds):
   1. Log in to X in your browser and open your profile: https://x.com/<your_handle>
   2. Open DevTools (Cmd/Ctrl+Shift+J), paste this whole file into the Console, press Enter.
   3. It scrolls your timeline, collects up to ~60 posts, prints JSON, and copies it to your clipboard.
   4. Save it as me.json (or paste it to your AI), then:  python -m xboss analyze me.json

 Nothing is sent anywhere. It only reads what your browser already shows you.
*/
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const num = (s) => {
    if (!s) return 0;
    const m = String(s).replace(/,/g, "").match(/([0-9.]+)\s*([KkMm]?)/);
    if (!m) return 0;
    const v = parseFloat(m[1]);
    return Math.round(v * ({ k: 1e3, m: 1e6 }[m[2].toLowerCase()] || 1));
  };
  const parseStats = (label) => {
    // aria-label like "3 replies, 1 repost, 6 likes, 2 bookmarks, 198 views"
    const out = { replies: 0, reposts: 0, likes: 0, bookmarks: 0, views: 0, quotes: 0 };
    if (!label) return out;
    label.split(",").forEach((part) => {
      const p = part.trim().toLowerCase();
      const n = num(p);
      if (p.includes("repl")) out.replies = n;
      else if (p.includes("repost") || p.includes("retweet")) out.reposts = n;
      else if (p.includes("like")) out.likes = n;
      else if (p.includes("bookmark")) out.bookmarks = n;
      else if (p.includes("view")) out.views = n;
      else if (p.includes("quote")) out.quotes = n;
    });
    return out;
  };

  const handle = (location.pathname.split("/")[1] || "").replace(/^@/, "");
  const q = (sel) => document.querySelector(sel);
  const txt = (el) => (el ? el.innerText.trim() : "");
  const profile = {
    handle,
    name: txt(q('[data-testid="UserName"]')).split("\n")[0] || null,
    bio: txt(q('[data-testid="UserDescription"]')) || null,
    bio_url: txt(q('[data-testid="UserUrl"]')) || null,
    category: txt(q('[data-testid="UserProfessionalCategory"]')) || null,
    joined: null,
    premium: !!(q('[data-testid="UserName"] [data-testid="icon-verified"]')),
    following: null,
    followers: null,
    pinned_text: null,
  };
  const joined = txt(q('[data-testid="UserJoinDate"]')).match(/Joined\s+([A-Za-z]+)\s+(\d{4})/);
  if (joined) {
    const months = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
    profile.joined = `${joined[2]}-${String(months[joined[1].slice(0, 3).toLowerCase()] || 1).padStart(2, "0")}`;
  }
  document.querySelectorAll('a[href$="/following"], a[href$="/verified_followers"], a[href$="/followers"]').forEach((a) => {
    const t = a.innerText.replace(/\n/g, " ");
    if (/Following/i.test(t)) profile.following = num(t);
    if (/Followers/i.test(t)) profile.followers = num(t);
  });

  const seen = new Map();
  const grab = () => {
    document.querySelectorAll('article[data-testid="tweet"]').forEach((a) => {
      const links = [...a.querySelectorAll('a[href*="/status/"]')].map((x) => x.getAttribute("href"));
      const link = links.find((h) => /\/status\/\d+$/.test(h));
      if (!link || seen.has(link)) return;
      const authorOk = link.toLowerCase().startsWith("/" + handle.toLowerCase() + "/");
      const t = a.querySelector('[data-testid="tweetText"]');
      const time = a.querySelector("time");
      const grp = a.querySelector('[role="group"][aria-label]');
      const ctx = txt(a.querySelector('[data-testid="socialContext"]'));
      const stats = parseStats(grp ? grp.getAttribute("aria-label") : "");
      const body = t ? t.innerText : "";
      const isRepost = /reposted/i.test(ctx);
      const isReply = /Replying to/.test(a.innerText);
      seen.set(link, {
        url: "https://x.com" + link,
        date: time ? time.getAttribute("datetime").slice(0, 10) : null,
        text: body,
        views: stats.views, likes: stats.likes, replies: stats.replies, reposts: stats.reposts, quotes: stats.quotes, bookmarks: stats.bookmarks,
        is_reply: isReply, is_repost: isRepost || !authorOk,
        is_quote: !!a.querySelector('[data-testid="quoteTweet"], [role="link"] [data-testid="tweetText"]') && !!t,
        has_media: !!a.querySelector('[data-testid="tweetPhoto"], video'),
        urls: [...a.querySelectorAll('[data-testid="tweetText"] a[href^="http"]')].map((x) => x.getAttribute("href")),
        mentions: (body.match(/(?<![\w@])@([A-Za-z0-9_]{1,15})/g) || []).map((m) => m.slice(1)),
        pinned: /pinned/i.test(ctx),
      });
    });
  };
  window.scrollTo(0, 0);
  await sleep(600);
  for (let i = 0; i < 25 && seen.size < 60; i++) {
    grab();
    window.scrollBy(0, 2000);
    await sleep(900);
  }
  grab();
  const posts = [...seen.values()];
  const pinned = posts.find((p) => p.pinned);
  if (pinned) profile.pinned_text = pinned.text;
  const out = { profile, posts, collected_at: new Date().toISOString(), source: "xboss/scripts/collect_profile.js" };
  const json = JSON.stringify(out, null, 2);
  console.log(json);
  try { await navigator.clipboard.writeText(json); console.log(`%c✓ ${posts.length} posts copied to clipboard as JSON. Save as me.json and run: python -m xboss analyze me.json`, "color:#4ade80;font-weight:bold"); }
  catch (e) { console.log(`%c${posts.length} posts collected. Copy the JSON above (clipboard write was blocked; click the page and re-run to allow it).`, "color:#f5c542;font-weight:bold"); }
  return out;
})();
