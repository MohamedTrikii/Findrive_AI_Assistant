"""Composants visuels (HTML/CSS) de l'interface conversationnelle d'AutoMind AI.

Tout le contenu dynamique est échappé avec html.escape. Les chaînes HTML sont
produites sur une seule ligne pour éviter que Markdown les interprète.
"""

from __future__ import annotations

from html import escape
from zlib import crc32

from .chatbot import describe_criteria, format_int

CSS = """
<style>
:root{
  --am-navy:#0f1b2d; --am-ink:#1e293b; --am-muted:#64748b; --am-bg:#f5f7fb; --am-card:#ffffff;
  --am-border:#e3e8f0; --am-blue:#2563eb; --am-blue-soft:#eaf1ff; --am-green:#15803d; --am-green-soft:#e7f6ec;
  --am-orange:#b45309; --am-orange-soft:#fff4e2; --am-shadow:0 1px 2px rgba(15,27,45,.04),0 8px 24px rgba(15,27,45,.07);
}
html, body, [data-testid="stAppViewContainer"]{background:var(--am-bg);}
#MainMenu, footer, [data-testid="stDecoration"]{visibility:hidden;height:0;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stMainBlockContainer"], .block-container{max-width:980px;padding-top:1.2rem;padding-bottom:7rem;}
[data-testid="InputInstructions"]{display:none;}
.st-key-scroller{height:0;overflow:hidden;margin:0;}
button:focus-visible{outline:2px solid var(--am-blue)!important;outline-offset:2px;}

/* ---------- barre supérieure */
.am-top{display:flex;align-items:center;gap:12px;}
.am-logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#1d4ed8,#0f1b2d);display:flex;align-items:center;justify-content:center;box-shadow:var(--am-shadow);flex:none;}
.am-title{font-size:1.2rem;font-weight:750;color:var(--am-navy);line-height:1.1;}
.am-title span{color:var(--am-blue);}
.am-sub{font-size:.8rem;color:var(--am-muted);display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
.am-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 3px #dcfce7;display:inline-block;}
.st-key-new_conv button{border-radius:999px;border:1px solid var(--am-border);background:#fff;font-weight:600;}
.st-key-new_conv button p{white-space:nowrap;font-size:.88rem;}
.st-key-new_conv button:hover{border-color:var(--am-blue);color:var(--am-blue);}

/* ---------- écran d'accueil */
.am-welcome{text-align:center;padding:5vh 8px 18px;}
.am-welcome-ico{width:64px;height:64px;margin:0 auto 16px;border-radius:18px;background:linear-gradient(135deg,#2563eb,#0f1b2d);display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(37,99,235,.25);}
.am-welcome h1{font-size:2.1rem;line-height:1.15;font-weight:780;color:var(--am-navy);margin:0 0 10px;padding:0;letter-spacing:-.02em;}
.am-welcome p{font-size:1.02rem;color:#475569;max-width:560px;margin:0 auto;line-height:1.55;}
.am-welcome-meta{margin-top:12px;font-size:.8rem;color:var(--am-muted);}
.st-key-welcome_cards{margin-top:14px;}
.st-key-welcome_cards button{min-height:76px;border-radius:16px;background:#fff;border:1px solid var(--am-border);box-shadow:var(--am-shadow);justify-content:flex-start;text-align:left;padding:12px 16px;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease;}
.st-key-welcome_cards button:hover{transform:translateY(-2px);border-color:#9db6f0;box-shadow:0 2px 4px rgba(15,27,45,.06),0 14px 30px rgba(15,27,45,.10);color:var(--am-navy);}
.st-key-welcome_cards button p{font-size:.95rem;font-weight:600;color:var(--am-navy);}
@media (max-width:640px){.am-welcome h1{font-size:1.6rem;}.am-welcome{padding-top:2vh;}}

/* ---------- messages */
[data-testid="stChatMessage"]{background:transparent;padding:6px 0;gap:12px;animation:am-in .22s ease-out;}
@keyframes am-in{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){flex-direction:row-reverse;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]{flex:0 1 auto;max-width:78%;background:var(--am-blue);color:#fff;padding:10px 15px;border-radius:18px 18px 4px 18px;box-shadow:0 4px 14px rgba(37,99,235,.18);}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] p{color:#fff;margin:0;}
[data-testid="stChatMessageAvatarUser"]{background:#dbe4f3;}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"]{min-width:0;}
.am-time{font-size:.68rem;color:#94a3b8;margin-top:6px;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .am-time{color:#dbe7ff;text-align:right;margin-top:3px;}

/* ---------- contenu des réponses */
.am-a-title{display:inline-flex;align-items:center;gap:6px;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--am-blue);background:var(--am-blue-soft);padding:3px 9px;border-radius:999px;margin-bottom:6px;}
.am-a-title.warn{color:var(--am-orange);background:var(--am-orange-soft);}
.am-a-title.muted{color:var(--am-muted);background:#eef1f6;}
.am-a-title.ok{color:var(--am-green);background:var(--am-green-soft);}
.am-a-text{font-size:.97rem;line-height:1.55;color:var(--am-ink);}
.am-crit-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:10px 0 2px;}
.am-crit-label{font-size:.8rem;font-weight:650;color:var(--am-muted);margin-right:2px;}
.am-crit{font-size:.8rem;background:var(--am-blue-soft);color:#1e3a8a;border:1px solid #cfdcfb;padding:3px 10px;border-radius:999px;}
.st-key-chips_live{gap:6px!important;align-items:center;margin-top:6px;}
.st-key-chips_live button{border-radius:999px;background:var(--am-blue-soft);border:1px solid #cfdcfb;color:#1e3a8a;min-height:30px;padding:1px 11px;}
.st-key-chips_live button p{font-size:.8rem;}
.st-key-chips_live button:hover{background:#fee2e2;border-color:#fca5a5;color:#991b1b;}
.am-changes{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;}
.am-change{font-size:.74rem;padding:2px 8px;border-radius:999px;border:1px solid var(--am-border);background:#fff;}
.am-change.add{border-color:#bfe3cb;color:var(--am-green);}
.am-change.chg{border-color:#c9d8fb;color:var(--am-blue);}
.am-change.del{border-color:#e7d3d3;color:#8a3b3b;text-decoration:line-through;}
.am-warn{margin-top:8px;font-size:.85rem;color:#7c3d06;background:var(--am-orange-soft);border:1px solid #f6d9a8;border-radius:10px;padding:8px 11px;}
.am-summary{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.8rem;color:#475569;margin:12px 0 2px;}
.am-summary b{color:var(--am-navy);}
.am-ask{font-size:.93rem;color:var(--am-ink);margin:12px 0 2px;}
.am-mini{font-size:.74rem;font-weight:650;color:var(--am-muted);text-transform:uppercase;letter-spacing:.05em;margin:10px 0 2px;}
[class*="st-key-actions_"], [class*="st-key-ask_"], [class*="st-key-relax_"], [class*="st-key-starters_"]{gap:6px!important;}
[class*="st-key-actions_"] button, [class*="st-key-ask_"] button, [class*="st-key-relax_"] button, [class*="st-key-starters_"] button{border-radius:999px;min-height:32px;padding:2px 13px;background:#fff;border:1px solid #c9d8fb;color:#1e3a8a;}
[class*="st-key-actions_"] button p, [class*="st-key-ask_"] button p, [class*="st-key-relax_"] button p, [class*="st-key-starters_"] button p{font-size:.82rem;}
[class*="st-key-actions_"] button:hover, [class*="st-key-ask_"] button:hover, [class*="st-key-relax_"] button:hover, [class*="st-key-starters_"] button:hover{background:var(--am-blue-soft);border-color:var(--am-blue);color:#1e3a8a;}
[class*="st-key-relax_"] button{border-color:#f3d19c;background:#fffaf0;color:#7c3d06;}
[class*="st-key-relax_"] button:hover{background:var(--am-orange-soft);border-color:#e9a23b;color:#7c3d06;}

/* ---------- carrousel de cartes */
[class*="st-key-carousel_"]{flex-wrap:nowrap!important;overflow-x:auto;scroll-snap-type:x mandatory;gap:12px!important;padding:8px 2px 10px;margin-top:6px;scrollbar-width:thin;}
[class*="st-key-carousel_"]::-webkit-scrollbar{height:6px;} [class*="st-key-carousel_"]::-webkit-scrollbar-thumb{background:#cfd7e3;border-radius:99px;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]{flex:0 0 238px!important;width:238px!important;min-width:238px;scroll-snap-align:start;}
[class*="st-key-card_"]{width:100%!important;height:100%;background:#fff;border:1px solid var(--am-border);border-radius:16px;overflow:hidden;box-shadow:var(--am-shadow);gap:0!important;padding-bottom:10px;transition:transform .15s ease,box-shadow .15s ease;}
[class*="st-key-card_"]:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgba(15,27,45,.06),0 14px 30px rgba(15,27,45,.11);}
[class*="st-key-card_"] [data-testid="stButton"]{padding:0 12px;}
[class*="st-key-card_"] button{width:100%;border-radius:10px;min-height:34px;background:var(--am-blue-soft);border:none;color:#1d4ed8;font-weight:650;}
[class*="st-key-card_"] button p{font-size:.84rem;}
[class*="st-key-card_"] button:hover{background:var(--am-blue);color:#fff;}
[class*="st-key-more_"] button{border-radius:999px;font-size:.82rem;}
.am-media{position:relative;height:110px;display:flex;align-items:center;justify-content:center;}
.am-media.Citadine{background:linear-gradient(135deg,#dbeafe,#f5f9ff);}
.am-media.Compacte{background:linear-gradient(135deg,#e0e7ff,#f7f5ff);}
.am-media.Berline{background:linear-gradient(135deg,#e2e8f0,#f8fafc);}
.am-media.SUV{background:linear-gradient(135deg,#d1fae5,#f3fdf7);}
.am-media-brand{position:absolute;left:12px;top:9px;font-size:.66rem;font-weight:750;letter-spacing:.12em;color:#334155;opacity:.55;text-transform:uppercase;}
.am-media-tag{position:absolute;right:10px;top:8px;font-size:.66rem;font-weight:700;padding:2px 7px;border-radius:6px;background:rgba(255,255,255,.88);color:#475569;}
.am-flags{position:absolute;left:10px;bottom:7px;display:flex;gap:4px;flex-wrap:wrap;}
.am-flag{font-size:.62rem;font-weight:700;padding:2px 7px;border-radius:6px;background:#0f1b2d;color:#fff;}
.am-flag.green{background:var(--am-green);}
.am-body{padding:10px 12px 10px;display:flex;flex-direction:column;gap:7px;}
.am-head{display:flex;justify-content:space-between;align-items:flex-start;gap:6px;}
.am-name{font-weight:700;color:var(--am-navy);font-size:.95rem;line-height:1.2;}
.am-meta{font-size:.76rem;color:var(--am-muted);margin-top:2px;}
.am-price{font-weight:800;color:var(--am-blue);font-size:1.05rem;white-space:nowrap;}
.am-price small{font-size:.68rem;font-weight:700;color:#5b7bd5;}
.am-chips{display:flex;flex-wrap:wrap;gap:4px;}
.am-chip{font-size:.68rem;font-weight:600;padding:2px 7px;border-radius:6px;background:#f1f5f9;color:#334155;}
.am-chip.Diesel{background:#fef3c7;color:#92400e;}
.am-chip.Essence{background:#dbeafe;color:#1e40af;}
.am-chip.Hybride{background:#dcfce7;color:#166534;}
.am-chip.Électrique{background:#cffafe;color:#155e75;}
.am-chip.on{box-shadow:inset 0 0 0 1.5px currentColor;}
.am-chip.on::before{content:"✓ ";}
.am-specs{display:flex;gap:10px;font-size:.76rem;color:#475569;flex-wrap:wrap;}
.am-specs span{display:inline-flex;align-items:center;gap:4px;}
.am-specs span.on{color:var(--am-green);font-weight:650;}

/* ---------- vue détaillée */
.am-detail{background:#fff;border:1px solid var(--am-border);border-radius:18px;overflow:hidden;box-shadow:var(--am-shadow);margin-top:6px;}
.am-detail .am-media{height:170px;}
.am-detail-body{padding:16px 18px;}
.am-detail-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;}
.am-detail-name{font-size:1.3rem;font-weight:780;color:var(--am-navy);line-height:1.15;}
.am-detail-price{font-size:1.45rem;font-weight:800;color:var(--am-blue);}
.am-spec-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:14px 0 4px;}
.am-spec{background:#f6f8fb;border:1px solid #eef1f6;border-radius:10px;padding:8px 10px;}
.am-spec small{display:block;font-size:.68rem;color:var(--am-muted);text-transform:uppercase;letter-spacing:.04em;}
.am-spec b{font-size:.9rem;color:var(--am-navy);}
.am-compare{margin:12px 0 0;padding:10px 12px;border-radius:10px;background:var(--am-blue-soft);font-size:.85rem;color:#1e3a8a;}
.am-compare ul{margin:4px 0 0 18px;padding:0;}
.am-note{font-size:.74rem;color:var(--am-muted);margin-top:10px;}
@media (max-width:640px){.am-spec-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}

/* ---------- état vide et indicateur de saisie */
.am-empty{display:flex;gap:12px;align-items:flex-start;margin-top:10px;padding:14px 16px;border:1px dashed #e2c48f;border-radius:14px;background:#fffaf0;}
.am-empty-ico{font-size:1.5rem;line-height:1;}
.am-empty b{color:#7c3d06;display:block;margin-bottom:2px;}
.am-empty span{font-size:.86rem;color:#8a5a1a;}
.am-typing{display:inline-flex;align-items:center;gap:10px;font-size:.88rem;color:var(--am-muted);}
.am-typing i{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--am-blue);opacity:.3;animation:am-blink 1s infinite;}
.am-typing i:nth-child(2){animation-delay:.15s;} .am-typing i:nth-child(3){animation-delay:.3s;}
@keyframes am-blink{0%,80%,100%{opacity:.25;transform:translateY(0);}40%{opacity:1;transform:translateY(-3px);}}

/* ---------- saisie */
[data-testid="stBottomBlockContainer"]{max-width:980px;padding-bottom:18px;background:linear-gradient(180deg,rgba(245,247,251,0),var(--am-bg) 30%);}
[data-testid="stChatInput"]{border-radius:18px;border:1px solid #cfd8e6;background:#fff;box-shadow:0 6px 24px rgba(15,27,45,.08);}
[data-testid="stChatInput"]:focus-within{border-color:var(--am-blue);box-shadow:0 0 0 3px rgba(37,99,235,.15),0 6px 24px rgba(15,27,45,.08);}
[data-testid="stChatInput"] textarea{font-size:.98rem;}

/* ---------- barre latérale */
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--am-border);}
.am-side-note{font-size:.8rem;color:var(--am-muted);line-height:1.45;}
.am-bar{display:flex;align-items:center;gap:8px;font-size:.8rem;margin:3px 0;}
.am-bar-lbl{width:78px;color:#334155;}
.am-bar-track{flex:1;height:7px;background:#eef1f6;border-radius:99px;overflow:hidden;}
.am-bar-fill{height:100%;background:var(--am-blue);border-radius:99px;}
.am-bar-val{width:28px;text-align:right;color:var(--am-muted);}

/* =====================================================================
   HABILLAGE ANIMÉ (prend le pas sur les règles ci-dessus)
   ===================================================================== */
:root{--am-grad:linear-gradient(135deg,#2563eb 0%,#4f46e5 55%,#7c3aed 100%);}

/* ---------- fond « aurore » animé */
[data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:-20%;z-index:0;pointer-events:none;
  background:radial-gradient(40% 35% at 15% 20%,rgba(37,99,235,.13),transparent 70%),
             radial-gradient(35% 30% at 85% 15%,rgba(124,58,237,.10),transparent 70%),
             radial-gradient(45% 40% at 70% 90%,rgba(14,165,233,.10),transparent 70%);
  animation:am-aurora 22s ease-in-out infinite alternate;}
[data-testid="stMain"], [data-testid="stBottom"]{position:relative;z-index:1;}
@keyframes am-aurora{0%{transform:translate3d(0,0,0) rotate(0deg);}50%{transform:translate3d(3%,-2%,0) rotate(4deg);}100%{transform:translate3d(-3%,2%,0) rotate(-3deg);}}

/* ---------- barre supérieure en verre dépoli, fixée en haut */
[data-testid="stLayoutWrapper"]:has(> .st-key-topbar){position:sticky;top:0;z-index:60;}
[data-testid="stMainBlockContainer"], .block-container{padding-bottom:2rem;}
.st-key-topbar{padding:10px 14px;margin:-6px -14px 6px;border-radius:0 0 18px 18px;
  background:rgba(245,247,251,.72);backdrop-filter:blur(14px) saturate(1.4);-webkit-backdrop-filter:blur(14px) saturate(1.4);
  border-bottom:1px solid rgba(227,232,240,.8);}
.am-logo{background:var(--am-grad);animation:am-logo 6s ease-in-out infinite;}
@keyframes am-logo{0%,100%{box-shadow:0 6px 18px rgba(37,99,235,.25);}50%{box-shadow:0 6px 26px rgba(124,58,237,.40);}}
.am-title span{background:var(--am-grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.am-dot{animation:am-ping 2s ease-out infinite;}
@keyframes am-ping{0%{box-shadow:0 0 0 0 rgba(34,197,94,.55);}100%{box-shadow:0 0 0 9px rgba(34,197,94,0);}}
.st-key-new_conv button{transition:all .2s ease;}
.st-key-new_conv button:hover{background:var(--am-grad);color:#fff;border-color:transparent;transform:translateY(-1px);box-shadow:0 8px 20px rgba(79,70,229,.30);}
.st-key-new_conv button:hover p{color:#fff;}

/* ---------- bandeau d'accueil */
.am-hero{position:relative;overflow:hidden;border-radius:26px;margin:10px 0 6px;padding:40px 36px 0;color:#fff;
  background:linear-gradient(135deg,#0b1424 0%,#13254a 55%,#1e1b4b 100%);box-shadow:0 24px 60px rgba(15,27,45,.28);
  animation:am-rise .7s cubic-bezier(.2,.8,.2,1) both;}
.am-glow{position:absolute;border-radius:50%;filter:blur(40px);opacity:.55;pointer-events:none;}
.am-glow.g1{width:320px;height:320px;left:-80px;top:-120px;background:#2563eb;animation:am-float 9s ease-in-out infinite;}
.am-glow.g2{width:280px;height:280px;right:-60px;top:-60px;background:#7c3aed;animation:am-float 11s ease-in-out infinite reverse;}
.am-glow.g3{width:240px;height:240px;left:40%;bottom:-140px;background:#0ea5e9;opacity:.35;animation:am-float 13s ease-in-out infinite;}
@keyframes am-float{0%,100%{transform:translate(0,0) scale(1);}50%{transform:translate(30px,20px) scale(1.12);}}
.am-hero-inner{position:relative;text-align:center;z-index:2;}
.am-hero-badge{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;font-weight:600;color:#c7d2fe;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);padding:6px 13px;border-radius:999px;
  animation:am-fade-up .6s .15s both;}
.am-hero h1{color:#fff;font-size:2.5rem;line-height:1.12;font-weight:800;letter-spacing:-.025em;margin:16px auto 12px;padding:0;max-width:640px;
  animation:am-fade-up .7s .25s both;}
.am-grad{background:linear-gradient(90deg,#60a5fa,#a78bfa,#f0abfc,#60a5fa);background-size:300% 100%;
  -webkit-background-clip:text;background-clip:text;color:transparent;animation:am-shimmer 6s linear infinite;}
@keyframes am-shimmer{to{background-position:300% 0;}}
.am-hero p{color:#cbd5e1;font-size:1.04rem;line-height:1.6;max-width:560px;margin:0 auto;animation:am-fade-up .7s .35s both;}
.am-stats{display:flex;justify-content:center;gap:12px;margin-top:22px;flex-wrap:wrap;animation:am-fade-up .7s .45s both;}
.am-stat{min-width:104px;padding:10px 16px;border-radius:14px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);}
.am-stat b{display:block;font-size:1.35rem;font-weight:800;color:#fff;line-height:1.1;}
.am-stat span{font-size:.74rem;color:#a5b4fc;text-transform:uppercase;letter-spacing:.06em;}
/* route animée */
.am-road{position:relative;height:96px;margin:26px -36px 0;overflow:hidden;
  background:linear-gradient(180deg,transparent 0%,transparent 48%,#0a1020 48%,#111a2e 100%);}
.am-lane{position:absolute;left:0;right:0;top:74px;height:3px;opacity:.7;
  background:repeating-linear-gradient(90deg,#fbbf24 0 34px,transparent 34px 70px);animation:am-lane 1.1s linear infinite;}
@keyframes am-lane{to{background-position:-70px 0;}}
.am-road-car{position:absolute;bottom:22px;left:-180px;animation:am-drive 9s linear infinite;filter:drop-shadow(0 6px 10px rgba(0,0,0,.45));}
.am-road-car.late{bottom:30px;animation-duration:13s;animation-delay:-6s;opacity:.85;transform:scale(.8);}
.am-road-car .am-wheel{animation:am-spin .55s linear infinite;}
.am-road-car .am-body-svg{animation:am-bob .45s ease-in-out infinite alternate;}
.am-road-car .am-light{animation:am-blink-light 1.2s ease-in-out infinite;}
@keyframes am-drive{0%{left:-180px;}100%{left:calc(100% + 40px);}}
@keyframes am-blink-light{50%{fill:#fff7cc;}}
.am-hero-hint{text-align:center;font-size:.8rem;color:var(--am-muted);margin:16px 0 2px;animation:am-fade-up .7s .6s both;}
/* cartes de suggestion */
.st-key-welcome_cards [data-testid="stColumn"] [data-testid="stElementContainer"],
.st-key-welcome_cards [data-testid="stColumn"] .stElementContainer{animation:am-fade-up .55s both;}
.st-key-welcome_cards [data-testid="stColumn"]:nth-child(1) [data-testid="stElementContainer"]:nth-child(1){animation-delay:.55s;}
.st-key-welcome_cards [data-testid="stColumn"]:nth-child(2) [data-testid="stElementContainer"]:nth-child(1){animation-delay:.65s;}
.st-key-welcome_cards [data-testid="stColumn"]:nth-child(1) [data-testid="stElementContainer"]:nth-child(2){animation-delay:.75s;}
.st-key-welcome_cards [data-testid="stColumn"]:nth-child(2) [data-testid="stElementContainer"]:nth-child(2){animation-delay:.85s;}
.st-key-welcome_cards button{position:relative;overflow:hidden;min-height:78px;border-radius:18px;padding:14px 46px 14px 18px;
  background:rgba(255,255,255,.85);backdrop-filter:blur(6px);border:1px solid var(--am-border);transition:all .25s cubic-bezier(.2,.8,.2,1);}
.st-key-welcome_cards button::after{content:"→";position:absolute;right:18px;top:50%;transform:translate(-6px,-50%);opacity:0;
  font-size:1.15rem;color:#4f46e5;transition:all .25s ease;}
.st-key-welcome_cards button:hover{transform:translateY(-4px);border-color:transparent;
  box-shadow:0 0 0 2px rgba(99,102,241,.55),0 18px 36px rgba(79,70,229,.18);background:#fff;}
.st-key-welcome_cards button:hover::after{opacity:1;transform:translate(0,-50%);}
.st-key-welcome_cards button:active{transform:translateY(-1px) scale(.99);}

/* ---------- messages : entrées glissées */
[data-testid="stChatMessage"]{animation:am-from-left .4s cubic-bezier(.2,.8,.2,1) both;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){animation-name:am-from-right;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]{
  background:var(--am-grad);box-shadow:0 10px 24px rgba(79,70,229,.25);}
[data-testid="stChatMessageAvatarCustom"], [data-testid="stChatMessageAvatarAssistant"]{background:var(--am-grad)!important;color:#fff!important;
  border-radius:12px!important;box-shadow:0 6px 16px rgba(79,70,229,.30);}
[data-testid="stChatMessageAvatarCustom"] *, [data-testid="stChatMessageAvatarAssistant"] *{color:#fff!important;}
@keyframes am-from-left{from{opacity:0;transform:translateX(-14px);}to{opacity:1;transform:none;}}
@keyframes am-from-right{from{opacity:0;transform:translateX(14px);}to{opacity:1;transform:none;}}
@keyframes am-fade-up{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
@keyframes am-rise{from{opacity:0;transform:translateY(18px) scale(.98);}to{opacity:1;transform:none;}}
@keyframes am-pop{0%{opacity:0;transform:scale(.85);}70%{transform:scale(1.04);}100%{opacity:1;transform:none;}}
.am-a-title{background:linear-gradient(90deg,#eef2ff,#eaf1ff);color:#4338ca;animation:am-pop .45s both;}
.am-a-title.warn{background:var(--am-orange-soft);color:var(--am-orange);}
.am-a-title.ok{background:var(--am-green-soft);color:var(--am-green);}
.am-a-title.muted{background:#eef1f6;color:var(--am-muted);}
.st-key-chips_live [data-testid="stElementContainer"], .am-crit, .am-change{animation:am-pop .4s both;}
.st-key-chips_live button{transition:all .18s ease;}
.st-key-chips_live button:hover{transform:translateY(-1px);}

/* ---------- cartes véhicules : cascade, survol, reflet, roues qui tournent */
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]{animation:am-fade-up .5s cubic-bezier(.2,.8,.2,1) both;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(2){animation-delay:.07s;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(3){animation-delay:.14s;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(4){animation-delay:.21s;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(5){animation-delay:.28s;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(6){animation-delay:.35s;}
[class*="st-key-carousel_"] > [data-testid="stLayoutWrapper"]:nth-child(n+7){animation-delay:.1s;}
[class*="st-key-card_"]{position:relative;transition:transform .3s cubic-bezier(.2,.8,.2,1),box-shadow .3s ease,border-color .3s ease;}
[class*="st-key-card_"]::after{content:"";position:absolute;top:0;left:-60%;width:40%;height:100%;pointer-events:none;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.55),transparent);transform:skewX(-18deg);opacity:0;}
[class*="st-key-card_"]:hover{transform:translateY(-6px);border-color:#c7d2fe;
  box-shadow:0 4px 8px rgba(15,27,45,.06),0 22px 40px rgba(79,70,229,.16);}
[class*="st-key-card_"]:hover::after{animation:am-shine .9s ease;}
@keyframes am-shine{0%{left:-60%;opacity:1;}100%{left:130%;opacity:0;}}
.am-car-svg{overflow:visible;transition:transform .5s cubic-bezier(.2,.8,.2,1);}
.am-wheel{transform-box:fill-box;transform-origin:center;}
.am-body-svg{transform-box:fill-box;transform-origin:center bottom;}
[class*="st-key-card_"]:hover .am-car-svg{transform:translateX(10px);}
[class*="st-key-card_"]:hover .am-wheel{animation:am-spin .5s linear infinite;}
[class*="st-key-card_"]:hover .am-body-svg{animation:am-bob .35s ease-in-out infinite alternate;}
@keyframes am-spin{to{transform:rotate(360deg);}}
@keyframes am-bob{to{transform:translateY(-1.2px);}}
.am-price{background:var(--am-grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.am-price small{color:#6366f1;-webkit-text-fill-color:#6366f1;}
.am-flag.green{animation:am-badge 2.4s ease-in-out infinite;}
@keyframes am-badge{0%,100%{box-shadow:0 0 0 0 rgba(21,128,61,.45);}50%{box-shadow:0 0 0 5px rgba(21,128,61,0);}}
[class*="st-key-card_"] button{transition:all .2s ease;}
[class*="st-key-card_"] button:hover{background:var(--am-grad);color:#fff;box-shadow:0 8px 18px rgba(79,70,229,.28);}
[class*="st-key-card_"] button:hover p{color:#fff;}

/* ---------- pastilles d'action */
[class*="st-key-actions_"] button, [class*="st-key-ask_"] button, [class*="st-key-starters_"] button, [class*="st-key-relax_"] button{
  transition:all .2s cubic-bezier(.2,.8,.2,1);}
[class*="st-key-actions_"] button:hover, [class*="st-key-ask_"] button:hover, [class*="st-key-starters_"] button:hover{
  transform:translateY(-2px);box-shadow:0 8px 18px rgba(37,99,235,.18);}
[class*="st-key-relax_"] button:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(217,119,6,.20);}
[class*="st-key-ask_"] [data-testid="stElementContainer"], [class*="st-key-actions_"] [data-testid="stElementContainer"],
[class*="st-key-relax_"] [data-testid="stElementContainer"]{animation:am-pop .45s .25s both;}
.am-ask{animation:am-fade-up .5s .2s both;}

/* ---------- fiche détaillée */
.am-detail{animation:am-rise .55s cubic-bezier(.2,.8,.2,1) both;}
.am-detail .am-media{background:radial-gradient(70% 90% at 50% 100%,rgba(99,102,241,.25),transparent 70%),linear-gradient(135deg,#e0e7ff,#f5f3ff);}
.am-detail .am-car-svg{animation:am-arrive .9s cubic-bezier(.2,.8,.2,1) both;}
.am-detail .am-wheel{animation:am-spin .45s linear 2;}
@keyframes am-arrive{from{transform:translateX(-120px);opacity:0;}to{transform:none;opacity:1;}}
.am-detail-price{background:var(--am-grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.am-spec{transition:transform .2s ease,border-color .2s ease;animation:am-fade-up .45s both;}
.am-spec:nth-child(2){animation-delay:.05s;} .am-spec:nth-child(3){animation-delay:.1s;} .am-spec:nth-child(4){animation-delay:.15s;}
.am-spec:nth-child(5){animation-delay:.2s;} .am-spec:nth-child(6){animation-delay:.25s;} .am-spec:nth-child(7){animation-delay:.3s;}
.am-spec:nth-child(8){animation-delay:.35s;}
.am-spec:hover{transform:translateY(-2px);border-color:#c7d2fe;}

/* ---------- état vide */
.am-empty{animation:am-rise .5s both;}
.am-empty-ico{display:inline-block;animation:am-search 2.4s ease-in-out infinite;}
@keyframes am-search{0%,100%{transform:translate(0,0) rotate(0);}25%{transform:translate(3px,-2px) rotate(8deg);}75%{transform:translate(-3px,1px) rotate(-6deg);}}

/* ---------- indicateur de recherche : piste + cartes fantômes */
.am-loading{animation:am-fade-up .3s both;}
.am-typing{gap:12px;font-weight:600;color:#4338ca;}
.am-track{position:relative;width:64px;height:22px;border-radius:999px;background:#eef2ff;overflow:hidden;
  box-shadow:inset 0 0 0 1px #c7d2fe;}
.am-track::after{content:"";position:absolute;left:0;right:0;top:50%;height:2px;margin-top:-1px;opacity:.6;
  background:repeating-linear-gradient(90deg,#a5b4fc 0 6px,transparent 6px 12px);animation:am-lane .5s linear infinite;}
.am-track-car{position:absolute;top:3px;left:-18px;z-index:1;animation:am-track 1.3s ease-in-out infinite;}
@keyframes am-track{0%{left:-18px;}100%{left:66px;}}
.am-skels{display:flex;gap:12px;margin-top:12px;overflow:hidden;}
.am-skel{flex:0 0 220px;height:188px;border-radius:16px;background:#fff;border:1px solid var(--am-border);padding:0 0 12px;overflow:hidden;}
.am-skel-img{height:96px;background:#eef2f7;}
.am-skel-l{height:10px;border-radius:6px;margin:12px 12px 0;background:#eef2f7;}
.am-skel-l.w1{width:70%;} .am-skel-l.w2{width:45%;} .am-skel-l.w3{width:85%;}
.am-skel-img, .am-skel-l{background:linear-gradient(90deg,#eef2f7 0%,#f8fafc 40%,#eef2f7 80%);background-size:200% 100%;
  animation:am-skel 1.2s ease-in-out infinite;}
@keyframes am-skel{from{background-position:200% 0;}to{background-position:-200% 0;}}

/* ---------- saisie : halo lumineux */
[data-testid="stChatInput"]{transition:box-shadow .25s ease,border-color .25s ease;}
[data-testid="stChatInput"]:focus-within{border-color:#818cf8;animation:am-halo 2.4s ease-in-out infinite;}
@keyframes am-halo{0%,100%{box-shadow:0 0 0 3px rgba(99,102,241,.16),0 10px 30px rgba(79,70,229,.14);}
  50%{box-shadow:0 0 0 5px rgba(99,102,241,.10),0 10px 34px rgba(124,58,237,.20);}}
[data-testid="stChatInputSubmitButton"]{background:var(--am-grad)!important;color:#fff!important;border-radius:12px!important;transition:transform .15s ease;}
[data-testid="stChatInputSubmitButton"]:hover{transform:scale(1.07);}
[data-testid="stChatInputSubmitButton"]:disabled{background:#e2e8f0!important;color:#94a3b8!important;}
[data-testid="stChatInputSubmitButton"] svg{color:inherit;fill:currentColor;}

@media (max-width:640px){
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar){position:static;}
  .st-key-topbar{margin:0 0 4px;padding:6px 4px;background:transparent;backdrop-filter:none;-webkit-backdrop-filter:none;border:none;}
  .st-key-topbar [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:8px;}
  .st-key-topbar [data-testid="stColumn"]{min-width:0!important;width:auto!important;flex:1 1 auto!important;}
  .st-key-topbar [data-testid="stColumn"]:last-child{flex:0 0 auto!important;}
  .am-sub{display:none;}
  .st-key-new_conv button{min-height:36px;padding:0 12px;}
  .am-hero{padding:22px 16px 0;border-radius:22px;margin-top:4px;}
  .am-hero h1{font-size:1.55rem;margin:12px auto 8px;}
  .am-hero p{font-size:.9rem;line-height:1.5;}
  .am-stats{flex-wrap:nowrap;gap:8px;margin-top:14px;}
  .am-stat{min-width:0;flex:1;padding:7px 6px;}
  .am-stat b{font-size:1.1rem;} .am-stat span{font-size:.64rem;}
  .am-road{margin:14px -16px 0;height:72px;}
  .am-lane{top:56px;}
  .am-road-car{bottom:16px;} .am-road-car svg{width:110px;height:auto;}
  .am-hero-hint{font-size:.74rem;margin:10px 0 0;}
  .st-key-welcome_cards [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:8px;}
  .st-key-welcome_cards [data-testid="stColumn"]{min-width:0!important;width:50%!important;flex:1 1 50%!important;}
  .st-key-welcome_cards button{min-height:64px;padding:10px 12px;border-radius:16px;}
  .st-key-welcome_cards button p{font-size:.82rem;}
  .st-key-welcome_cards button::after{display:none;}
  .am-skel{flex-basis:170px;}
}
/* Respect de la préférence système « réduire les animations » */
@media (prefers-reduced-motion: reduce){
  *, *::before, *::after{animation:none!important;transition:none!important;}
  .am-road-car{left:40%;}
}
</style>
"""

ICON_CAR = ('<svg width="{w}" height="{h}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 17h-1a1 1 0 0 1-1-1v-3.5l2.2-5A2 2 0 0 1 7 6h10a2 2 0 '
            '0 1 1.8 1.2l2.2 5V16a1 1 0 0 1-1 1h-1"/><path d="M3 12.5h18"/><circle cx="7.5" cy="17" r="2"/>'
            '<circle cx="16.5" cy="17" r="2"/><path d="M9.5 17h5"/></svg>')
ICON_PIN = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12Z"/>'
            '<circle cx="12" cy="9" r="2.5"/></svg>')
ICON_GAUGE = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" aria-hidden="true"><path d="M12 14l4-4"/><path d="M3.3 19a10 10 0 1 1 17.4 0"/></svg>')
ICON_CAL = ('<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>')

SILHOUETTE = {
    "SUV": "M10 50 L10 36 Q12 30 20 29 L34 27 L46 15 Q50 12 58 12 L100 12 Q108 12 112 18 L122 29 Q132 31 134 38 L134 50 Z",
    "Berline": "M8 50 L8 40 Q10 34 18 33 L36 31 L52 19 Q57 16 64 16 L92 16 Q100 16 106 22 L116 31 Q132 33 136 40 L136 50 Z",
    "Compacte": "M10 50 L10 39 Q12 33 20 32 L36 30 L50 17 Q54 14 62 14 L100 14 Q108 14 114 22 L124 32 Q132 34 134 40 L134 50 Z",
    "Citadine": "M14 50 L14 39 Q15 33 22 32 L38 30 L52 17 Q56 14 64 14 L96 14 Q104 14 110 21 L120 32 Q128 34 130 40 L130 50 Z",
}
WINDOWS = {
    "SUV": "M50 17 Q53 15 59 15 L98 15 Q104 15 108 20 L116 28 L44 28 Z",
    "Berline": "M56 21 Q60 19 65 19 L91 19 Q97 19 102 24 L110 31 L42 31 Z",
    "Compacte": "M54 19 Q57 17 63 17 L99 17 Q105 17 109 23 L118 31 L42 31 Z",
    "Citadine": "M56 19 Q59 17 65 17 L95 17 Q101 17 106 22 L115 31 L44 31 Z",
}
# Teintes de carrosserie : choisies de façon déterministe à partir de l'identifiant (illustration).
PAINTS = ["#1f2937", "#94a3b8", "#f8fafc", "#2563eb", "#b91c1c", "#475569", "#0f766e", "#d4d4d8"]

INTENT_TITLES = {
    "search": ("Recherche", ""),
    "follow_up": ("Recherche mise à jour", ""),
    "sort": ("Nouvel ordre", ""),
    "reset": ("Nouvelle recherche", "muted"),
    "no_criteria": ("Toutes les annonces", "muted"),
    "ambiguous": ("Précision nécessaire", "warn"),
    "unsupported": ("Hors de mon périmètre", "warn"),
    "help": ("Comment je fonctionne", "muted"),
    "manual": ("Filtres manuels", ""),
    "detail": ("Détails du véhicule", "ok"),
}


def _wheel(cx: int) -> str:
    """Roue avec rayons : elle tourne quand la carte est survolée (CSS .am-wheel)."""
    return (f'<g class="am-wheel"><circle cx="{cx}" cy="50" r="9" fill="#111827"/>'
            f'<circle cx="{cx}" cy="50" r="4.5" fill="#cbd5e1"/>'
            f'<path d="M{cx} 45.5V54.5M{cx - 4.5} 50H{cx + 4.5}" stroke="#64748b" stroke-width="1.3"/></g>')


def car_svg(category: str, paint: str, width: int = 160, label: str = "") -> str:
    return (f'<svg class="am-car-svg" width="{width}" height="{round(width * 62 / 144)}" viewBox="0 0 144 62" '
            f'role="img" aria-label="{escape(label)}">'
            '<ellipse class="am-shadow-svg" cx="72" cy="57" rx="62" ry="4" fill="#0f1b2d" opacity=".10"/>'
            '<g class="am-body-svg">'
            f'<path d="{SILHOUETTE.get(category, SILHOUETTE["Compacte"])}" fill="{paint}" stroke="#334155" stroke-width="1.2"/>'
            f'<path d="{WINDOWS.get(category, WINDOWS["Compacte"])}" fill="#bfd3ea" opacity=".85"/>'
            '<path d="M60 26 L74 18" stroke="#fff" stroke-width="2" opacity=".35" stroke-linecap="round"/>'
            '<rect class="am-light" x="126" y="36" width="7" height="3" rx="1.5" fill="#fbbf24"/></g>'
            f'{_wheel(38)}{_wheel(106)}</svg>')


def car_image_svg(car: dict, width: int = 160) -> str:
    paint = PAINTS[crc32(car["id"].encode()) % len(PAINTS)]
    return car_svg(car["categorie"], paint, width, f'Illustration {car["marque"]} {car["modele"]}')


def top_bar_html() -> str:
    return (f'<div class="am-top"><div class="am-logo">{ICON_CAR.format(w=23, h=23, c="#fff")}</div><div>'
            '<div class="am-title">AutoMind <span>AI</span></div>'
            '<div class="am-sub"><span class="am-dot"></span>Assistant prêt · recherche automobile par conversation'
            '</div></div></div>')


def welcome_html(total: int, brands: int, cities: int) -> str:
    stats = "".join(f'<div class="am-stat"><b>{escape(v)}</b><span>{escape(label)}</span></div>'
                    for v, label in ((format_int(total), "annonces"), (str(brands), "marques"), (str(cities), "villes")))
    return ('<div class="am-hero">'
            '<div class="am-glow g1"></div><div class="am-glow g2"></div><div class="am-glow g3"></div>'
            '<div class="am-hero-inner">'
            '<div class="am-hero-badge"><span class="am-dot"></span>Assistant prêt · recherche par conversation</div>'
            '<h1>Votre prochaine voiture <span class="am-grad">commence ici.</span></h1>'
            '<p>Décrivez simplement la voiture que vous recherchez. Je m\'occupe de trouver les modèles '
            'qui correspondent à vos besoins.</p>'
            f'<div class="am-stats">{stats}</div></div>'
            '<div class="am-road"><div class="am-lane"></div>'
            f'<div class="am-road-car">{car_svg("SUV", "#2563eb", 150, "Voiture animée")}</div>'
            f'<div class="am-road-car late">{car_svg("Citadine", "#f8fafc", 120, "Voiture animée")}</div></div>'
            '</div>'
            '<div class="am-hero-hint">Choisissez une idée pour commencer, ou écrivez votre propre demande en bas '
            'de la page · données fictives de démonstration</div>')


def typing_html(text: str = "Je recherche les véhicules correspondants…") -> str:
    """Indicateur de traitement : petite voiture sur une piste + cartes « fantômes » scintillantes."""
    skeleton = "".join('<div class="am-skel"><div class="am-skel-img"></div><div class="am-skel-l w1"></div>'
                       '<div class="am-skel-l w2"></div><div class="am-skel-l w3"></div></div>' for _ in range(3))
    return ('<div class="am-loading"><div class="am-typing">'
            f'<div class="am-track"><span class="am-track-car">{ICON_CAR.format(w=16, h=16, c="#2563eb")}</span></div>'
            f'{escape(text)}</div><div class="am-skels">{skeleton}</div></div>')


def time_html(time: str) -> str:
    return f'<div class="am-time">{escape(time)}</div>' if time else ""


def answer_head_html(intent: str | None, text: str, title: str | None = None) -> str:
    label, tone = INTENT_TITLES.get(intent or "", ("", ""))
    label = title or label
    pill = f'<div class="am-a-title {tone}">{escape(label)}</div>' if label else ""
    return f'{pill}<div class="am-a-text">{escape(text)}</div>'


def chip_items(criteria: dict) -> list[tuple[str, str, str | None]]:
    """Puces compactes (clé, texte, valeur unitaire) : « Peugeot », « Budget ≤ 40 000 DT », « ≤ 120 000 km »…
    Un critère à plusieurs valeurs donne une puce par valeur."""
    items: list[tuple[str, str, str | None]] = []
    for key in ("marque", "modele", "carburant", "boite", "categorie", "ville"):
        value = criteria.get(key)
        if isinstance(value, list):
            items += [(key, str(v), v) for v in value]
        elif value is not None:
            items.append((key, str(value), None))
    # Bornes numériques : « _strict » = True → borne exclue (« moins de 40 000 DT » → « < »).
    bounds = (("prix_min", "Budget", "≥", ">", "DT"), ("prix_max", "Budget", "≤", "<", "DT"),
              ("kilometrage_min", "", "≥", ">", "km"), ("kilometrage_max", "", "≤", "<", "km"))
    for key, prefix, inclusive, strict, unit in bounds:
        if criteria.get(key) is None:
            continue
        sign = strict if criteria.get(f"{key}_strict") else inclusive
        items.append((key, f"{prefix} {sign} {format_int(criteria[key])} {unit}".strip(), None))
    for label, value in describe_criteria(criteria):
        if label.startswith("Ann"):
            text = {"Année minimum": f"Année ≥ {value}", "Année maximum": f"Année ≤ {value}"}.get(label, f"Année {value}")
            items.append(("annee_min", text, None))
    return items


def criteria_row_html(criteria: dict) -> str:
    items = chip_items(criteria)
    if not items:
        return ""
    chips = "".join(f'<span class="am-crit">{escape(text)}</span>' for _, text, _ in items)
    return f'<div class="am-crit-row"><span class="am-crit-label">🔎 Recherche :</span>{chips}</div>'


def changes_html(added: list, changed: list, removed: list) -> str:
    chips = [f'<span class="am-change add">+ {escape(label)} : {escape(v)}</span>' for label, v in added]
    chips += [f'<span class="am-change chg">⇄ {escape(label)} : {escape(v)}</span>' for label, v in changed]
    chips += [f'<span class="am-change del">{escape(label)}</span>' for label in removed]
    return f'<div class="am-changes">{"".join(chips)}</div>' if chips else ""


def warnings_html(warnings: list[str]) -> str:
    return "".join(f'<div class="am-warn">⚠ {escape(w)}</div>' for w in warnings)


def summary_html(cars: list[dict], sort: str) -> str:
    if not cars:
        return ""
    prices = [c["prix"] for c in cars]
    return ('<div class="am-summary">'
            f'<span>Prix : <b>{format_int(min(prices))} – {format_int(max(prices))} DT</b></span>'
            f'<span>Moyenne : <b>{format_int(round(sum(prices) / len(prices)))} DT</b></span>'
            f'<span>Ordre : <b>{escape(sort.lower())}</b></span></div>')


def car_card_html(car: dict, criteria: dict | None = None, flags: list[str] | None = None) -> str:
    criteria = criteria or {}
    fuel, cat = escape(car["carburant"]), escape(car["categorie"])

    def on(key: str) -> str:
        return " on" if criteria.get(key) is not None else ""

    year_on = "on" if (criteria.get("annee_min") or criteria.get("annee_max")) else ""
    flags_html = "".join(f'<span class="am-flag{" green" if f == "Meilleur prix" else ""}">{escape(f)}</span>'
                         for f in flags or [])
    return (
        f'<div class="am-media {cat}"><span class="am-media-brand">{escape(car["marque"])}</span>'
        f'<span class="am-media-tag">{car["annee"]}</span>{car_image_svg(car, 150)}'
        f'<div class="am-flags">{flags_html}</div></div>'
        '<div class="am-body"><div class="am-head"><div>'
        f'<div class="am-name">{escape(car["marque"])} {escape(car["modele"])}</div>'
        f'<div class="am-meta">{car["annee"]} · {escape(car["ville"])}</div></div>'
        f'<div class="am-price">{format_int(car["prix"])} <small>DT</small></div></div>'
        f'<div class="am-chips"><span class="am-chip {fuel}{on("carburant")}">{fuel}</span>'
        f'<span class="am-chip{on("boite")}">{escape(car["boite"])}</span>'
        f'<span class="am-chip{on("categorie")}">{cat}</span></div>'
        f'<div class="am-specs"><span class="{on("kilometrage_max").strip()}">{ICON_GAUGE}{format_int(car["kilometrage"])} km</span>'
        f'<span class="{year_on}">{ICON_CAL}{car["annee"]}</span>'
        f'<span class="{on("ville").strip()}">{ICON_PIN}{escape(car["ville"])}</span></div></div>'
    )


def detail_html(car: dict, comparison: list[str]) -> str:
    specs = [("Année", str(car["annee"])), ("Kilométrage", f'{format_int(car["kilometrage"])} km'),
             ("Carburant", car["carburant"]), ("Boîte", car["boite"]), ("Catégorie", car["categorie"]),
             ("État", car["etat"]), ("Ville", car["ville"]), ("Référence", car["id"])]
    grid = "".join(f'<div class="am-spec"><small>{escape(k)}</small><b>{escape(v)}</b></div>' for k, v in specs)
    compare = ""
    if comparison:
        items = "".join(f"<li>{escape(c)}</li>" for c in comparison)
        compare = f'<div class="am-compare"><b>Comparaison avec votre recherche</b><ul>{items}</ul></div>'
    origin = "annonce de test fixe" if car.get("source") == "fixture" else "annonce synthétique"
    return (
        f'<div class="am-detail"><div class="am-media {escape(car["categorie"])}">'
        f'<span class="am-media-brand">{escape(car["marque"])}</span>'
        f'<span class="am-media-tag">{car["annee"]}</span>{car_image_svg(car, 260)}</div>'
        '<div class="am-detail-body"><div class="am-detail-head"><div>'
        f'<div class="am-detail-name">{escape(car["marque"])} {escape(car["modele"])}</div>'
        f'<div class="am-meta">{escape(car["categorie"])} · {escape(car["carburant"])} · {escape(car["boite"])} · '
        f'{escape(car["ville"])}</div></div>'
        f'<div class="am-detail-price">{format_int(car["prix"])} DT</div></div>'
        f'<div class="am-spec-grid">{grid}</div>{compare}'
        f'<div class="am-note">Données fictives ({origin}) : le prix n\'est pas une cote du marché.</div>'
        '</div></div>'
    )


def empty_html() -> str:
    return ('<div class="am-empty"><div class="am-empty-ico">🔍</div><div>'
            '<b>Aucune voiture ne correspond exactement.</b>'
            '<span>Choisissez une piste ci-dessous pour élargir la recherche, ou reformulez votre demande.</span>'
            '</div></div>')


def bars_html(counts: dict, total: int) -> str:
    rows = []
    for label, n in counts.items():
        pct = 100 * n / total if total else 0
        rows.append(f'<div class="am-bar"><span class="am-bar-lbl">{escape(str(label))}</span>'
                    f'<span class="am-bar-track"><span class="am-bar-fill" style="width:{pct:.0f}%;display:block"></span></span>'
                    f'<span class="am-bar-val">{n}</span></div>')
    return "".join(rows)
