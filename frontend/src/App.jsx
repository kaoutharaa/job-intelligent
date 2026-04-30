import { useState, useEffect, useRef } from "react";

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000";
const SESSION_DURATION = 60 * 60 * 1000; // 1 hour in milliseconds

// ─── STYLES ──────────────────────────────────────────────────────────────────
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    /* ── DARK MODE (Défaut) ── */
    --bg:        #0a0a0f;
    --bg2:       #111118;
    --bg3:       #1a1a24;
    --border:    rgba(255,255,255,0.07);
    --accent:    #6c63ff;
    --accent2:   #ff6b6b;
    --accent3:   #00d4aa;
    --text:      #f0f0f8;
    --muted:     #7a7a9a;
    --card:      rgba(255,255,255,0.03);
    --nav-bg:    rgba(10,10,15,0.8);
  }

  /* ── LIGHT MODE ── */
  body[data-theme='light'] {
    --bg:        #ffffff;
    --bg2:       #f5f7fa;
    --bg3:       #ffffff;
    --border:    rgba(0,0,0,0.1);
    --text:      #3498db; 
    --muted:     #8fa2b4;
    --card:      rgba(0,0,0,0.02);
    --nav-bg:    rgba(255,255,255,0.8);
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    line-height: 1.6;
    min-height: 100vh;
    overflow-x: hidden;
    transition: background-color 0.3s ease, color 0.3s ease;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 999;
    opacity: 0.4;
  }
  body[data-theme='light']::before { opacity: 0.08; }

  /* ── NAV ── */
  nav {
    position: fixed;
    top: 0; left: 0; right: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 3rem;
    background: var(--nav-bg);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border);
    z-index: 100;
    transition: background-color 0.3s ease, border-color 0.3s ease;
  }
  .nav-logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.2rem;
    letter-spacing: -0.02em;
  }
  .nav-logo span { color: var(--accent); }
  
  .nav-right { display: flex; align-items: center; gap: 2rem; }
  .nav-steps { display: flex; gap: 2rem; list-style: none; }
  .nav-steps li {
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    cursor: pointer;
    transition: color 0.2s;
  }
  .nav-steps li.active { color: var(--text); font-weight: 500; }
  .nav-steps li:hover { color: var(--text); }

  .theme-toggle {
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.5rem 0.8rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.8rem;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s;
  }
  .theme-toggle:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 4px 12px rgba(108,99,255,0.1);
  }
  
  .logout-btn {
    background: transparent;
    border: 1px solid var(--accent2);
    color: var(--accent2);
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.75rem;
    text-transform: uppercase;
    transition: all 0.2s;
  }
  .logout-btn:hover { background: rgba(255,107,107,0.1); }

  /* ── HERO ── */
  .hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 8rem 2rem 4rem;
    position: relative;
  }
  .hero-glow {
    position: absolute;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(108,99,255,0.15) 0%, transparent 70%);
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
  }
  .hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(108,99,255,0.1);
    border: 1px solid rgba(108,99,255,0.3);
    border-radius: 100px;
    padding: 0.35rem 1rem;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 2rem;
  }
  .hero-tag::before {
    content: '';
    width: 6px; height: 6px;
    background: var(--accent);
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
  }
  h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: clamp(2.5rem, 6vw, 5rem);
    line-height: 1.05;
    letter-spacing: -0.03em;
    margin-bottom: 1.5rem;
    max-width: 800px;
  }
  h1 em {
    font-style: normal;
    background: linear-gradient(135deg, var(--accent), var(--accent3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .hero-sub {
    font-size: 1.1rem;
    color: var(--muted);
    max-width: 500px;
    margin-bottom: 3rem;
    font-weight: 300;
  }
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    background: var(--accent);
    color: white;
    border: none;
    padding: 0.9rem 2rem;
    border-radius: 12px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.01em;
  }
  .btn-primary:hover {
    background: #7c73ff;
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(108,99,255,0.35);
  }
  .btn-primary:active { transform: translateY(0); }
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--border);
    padding: 0.9rem 2rem;
    border-radius: 12px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-secondary:hover { border-color: rgba(108,99,255,0.2); color: var(--text); }
  body[data-theme='light'] .btn-secondary:hover { border-color: var(--accent); }
  .hero-actions { display: flex; gap: 1rem; align-items: center; }

  /* ── STATS BAR ── */
  .stats-bar {
    display: flex;
    gap: 3rem;
    margin-top: 5rem;
    padding-top: 3rem;
    border-top: 1px solid var(--border);
  }
  .stat-item { text-align: center; }
  .stat-num { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: var(--text); }
  .stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 0.2rem; }

  /* ── SECTIONS ── */
  section { max-width: 900px; margin: 0 auto; padding: 5rem 2rem; }
  .section-label {
    font-size: 0.75rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 0.8rem; font-weight: 500;
  }
  h2 {
    font-family: 'Syne', sans-serif; font-weight: 700;
    font-size: clamp(1.8rem, 3vw, 2.5rem); letter-spacing: -0.02em; margin-bottom: 0.5rem;
  }
  .section-desc { color: var(--muted); margin-bottom: 2.5rem; font-size: 1rem; }

  /* ── FORMS ── */
  .form-grid { display: grid; gap: 1.2rem; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }
  .field { display: flex; flex-direction: column; gap: 0.5rem; }
  label { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); font-weight: 500; }
  input {
    background: var(--bg3); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.8rem 1rem; color: var(--text); font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem; font-weight: 300; outline: none; transition: all 0.2s ease; width: 100%;
  }
  input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(108,99,255,0.15); }
  input::placeholder { color: var(--muted); opacity: 0.6; }

  /* Password Wrapper for Eye Icon */
  .password-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }
  .password-wrapper input {
    padding-right: 2.5rem; /* Make room for the icon */
  }
  .password-toggle {
    position: absolute;
    right: 0.8rem;
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: color 0.2s;
  }
  .password-toggle:hover {
    color: var(--text);
  }

  /* ── AUTH BOX ── */
  .auth-box {
    max-width: 500px;
    margin: 0 auto;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 3rem 2.5rem;
    box-shadow: 0 20px 40px rgba(0,0,0,0.2);
  }
  .auth-toggle {
    text-align: center; margin-top: 1.5rem; font-size: 0.85rem; color: var(--muted);
  }
  .auth-toggle span {
    color: var(--accent); cursor: pointer; font-weight: 500; transition: color 0.2s;
  }
  .auth-toggle span:hover { color: #8e85ff; }

  /* ── CV UPLOAD ── */
  .cv-drop {
    border: 2px dashed var(--border); border-radius: 12px; padding: 2.5rem;
    text-align: center; cursor: pointer; transition: all 0.2s; position: relative; background: var(--bg3);
  }
  .cv-drop:hover { border-color: var(--accent); background: rgba(108,99,255,0.04); }
  .cv-drop input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
  .cv-icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
  .cv-drop p { color: var(--muted); font-size: 0.9rem; }
  .cv-drop strong { color: var(--text); }
  .cv-uploaded {
    display: flex; align-items: center; gap: 1rem; background: rgba(0,212,170,0.08);
    border: 1px solid rgba(0,212,170,0.2); border-radius: 10px; padding: 1rem 1.2rem;
  }
  .cv-uploaded-icon { font-size: 1.5rem; }
  .cv-uploaded-name { font-size: 0.9rem; color: var(--accent3); font-weight: 500; }
  .cv-uploaded-size { font-size: 0.8rem; color: var(--muted); }
  .cv-remove { margin-left: auto; background: none; border: none; color: var(--muted); cursor: pointer; font-size: 1.2rem; }
  .cv-remove:hover { color: var(--accent2); }

  .form-actions { display: flex; gap: 1rem; justify-content: flex-end; margin-top: 0.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }

  /* ── LOADING ── */
  .loading-state { text-align: center; padding: 6rem 2rem; }
  .loader {
    width: 48px; height: 48px; border: 3px solid var(--border); border-top-color: var(--accent);
    border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 2rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 600; margin-bottom: 0.5rem; }
  .loading-steps { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 2rem; align-items: center; }
  .loading-step { font-size: 0.85rem; color: var(--muted); display: flex; align-items: center; gap: 0.5rem; transition: color 0.4s; }
  .loading-step.done { color: var(--accent3); }
  .loading-step.active { color: var(--text); }

  /* ── RESULTS ── */
  .results-header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem; }
  .results-count { font-family: 'Syne', sans-serif; font-size: 1rem; color: var(--muted); }
  .results-count strong { color: var(--accent3); font-size: 1.4rem; }
  .filters { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 2rem; }
  .filter-btn {
    background: var(--bg3); border: 1px solid var(--border); color: var(--muted);
    padding: 0.4rem 0.9rem; border-radius: 8px; font-size: 0.8rem; cursor: pointer; transition: all 0.15s; font-family: 'DM Sans', sans-serif;
  }
  .filter-btn:hover, .filter-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(108,99,255,0.08); }

  /* ── JOB CARDS ── */
  .jobs-grid { display: grid; gap: 1rem; }
  .job-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 1.5rem; transition: all 0.2s; cursor: pointer; position: relative; overflow: hidden;
  }
  .job-card::before {
    content: ''; position: absolute; inset: 0; background: linear-gradient(135deg, rgba(108,99,255,0.04) 0%, transparent 60%); opacity: 0; transition: opacity 0.2s;
    pointer-events: none; /* This stops the overlay from blocking your clicks! */
  }
  .job-card:hover { border-color: rgba(108,99,255,0.3); transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
  body[data-theme='light'] .job-card:hover { box-shadow: 0 8px 32px rgba(0,0,0,0.08); }
  .job-card:hover::before { opacity: 1; }
  .job-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 0.8rem; }
  .job-score { display: flex; flex-direction: column; align-items: center; background: rgba(108,99,255,0.1); border: 1px solid rgba(108,99,255,0.2); border-radius: 10px; padding: 0.5rem 0.8rem; min-width: 60px; text-align: center; flex-shrink: 0; }
  .job-score-num { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--accent); line-height: 1; }
  .job-score-label { font-size: 0.6rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.2rem; }
  .job-title { font-family: 'Syne', sans-serif; font-size: 1.05rem; font-weight: 600; line-height: 1.3; margin-bottom: 0.3rem; }
  .job-company { color: var(--muted); font-size: 0.9rem; }
  .job-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.8rem 0; }
  .job-meta-item { display: flex; align-items: center; gap: 0.3rem; font-size: 0.8rem; color: var(--muted); }
  .job-skills { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.8rem; }
  .skill-badge { background: var(--bg3); border: 1px solid var(--border); color: var(--muted); padding: 0.2rem 0.6rem; border-radius: 5px; font-size: 0.75rem; }
  .job-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
  .source-badge { font-size: 0.7rem; letter-spacing: 0.05em; text-transform: uppercase; padding: 0.2rem 0.6rem; border-radius: 5px; }
  .source-badge.linkedin { background: rgba(0,119,181,0.15); color: #4da6d7; border: 1px solid rgba(0,119,181,0.2); }
  .source-badge.france_travail { background: rgba(255,107,107,0.1); color: #ff8c8c; border: 1px solid rgba(255,107,107,0.2); }
  .job-link { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.8rem; color: var(--accent); text-decoration: none; transition: gap 0.2s; }
  .job-link:hover { gap: 0.5rem; }
  .empty-state { text-align: center; padding: 5rem 2rem; color: var(--muted); }
  .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
  .cat-chip { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 5px; background: rgba(108,99,255,0.1); color: var(--accent); border: 1px solid rgba(108,99,255,0.2); margin-top: 0.3rem; }
  .match-bar { height: 3px; background: var(--bg3); border-radius: 3px; margin-top: 0.8rem; overflow: hidden; }
  .match-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent3)); border-radius: 3px; transition: width 0.8s ease; }

  /* ── DASHBOARD ── */
  .dashboard-shell { display: grid; gap: 1.3rem; }
  .dashboard-hero {
    background: linear-gradient(135deg, rgba(108,99,255,0.12), rgba(0,212,170,0.08));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.3rem 1.4rem;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .dashboard-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
  }
  .kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 10px 24px rgba(0,0,0,0.08);
  }
  .kpi-value { font-family: 'Syne', sans-serif; font-size: 1.55rem; font-weight: 700; line-height: 1.2; }
  .kpi-label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.35rem; }
  .dashboard-grid-2 {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
  .dashboard-section {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
  }
  .dashboard-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.8rem;
    gap: 0.8rem;
  }
  .dashboard-title { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; }
  .dashboard-list { display: grid; gap: 0.55rem; }
  .dashboard-list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.8rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.65rem 0.75rem;
    background: var(--bg3);
  }
  .dashboard-item-main { font-size: 0.9rem; color: var(--text); }
  .dashboard-count-pill {
    font-size: 0.75rem;
    color: var(--accent);
    background: rgba(108,99,255,0.12);
    border: 1px solid rgba(108,99,255,0.25);
    border-radius: 999px;
    padding: 0.2rem 0.55rem;
    white-space: nowrap;
  }
  .dashboard-chip-cloud { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .dashboard-chip {
    border: 1px solid var(--border);
    background: var(--bg3);
    color: var(--text);
    border-radius: 999px;
    padding: 0.35rem 0.65rem;
    font-size: 0.78rem;
  }
  .timeline-table { display: grid; gap: 0.5rem; }
  .timeline-row {
    display: grid;
    grid-template-columns: 1.3fr 1fr auto;
    gap: 0.6rem;
    align-items: center;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.6rem 0.7rem;
    background: var(--bg3);
  }
  .timeline-cell { color: var(--muted); font-size: 0.82rem; }
  .timeline-cell strong { color: var(--text); font-weight: 500; }
  .layer-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.8rem;
  }
  .layer-card {
    background: linear-gradient(140deg, rgba(108,99,255,0.08), rgba(108,99,255,0.02));
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
  }
  .layer-name { font-size: 0.82rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .layer-value { font-family: 'Syne', sans-serif; font-size: 1.2rem; margin-top: 0.3rem; }

  @media (max-width: 640px) {
    nav { padding: 1rem 1.5rem; }
    .nav-right { gap: 1rem; }
    .nav-steps { display: none; }
    .hero { padding: 6rem 1.5rem 3rem; }
    .form-row { grid-template-columns: 1fr; }
    .stats-bar { gap: 1.5rem; flex-wrap: wrap; justify-content: center; }
    section { padding: 3rem 1.5rem; }
    .auth-box { padding: 2rem 1.5rem; border-radius: 0; border-left: none; border-right: none; }
    .dashboard-grid-2 { grid-template-columns: 1fr; }
    .timeline-row { grid-template-columns: 1fr; }
    .dashboard-hero { padding: 1rem; }
  }
`;

function computeScore(job, profile) {
  let score = 0;
  const titleLower = (job.title || "").toLowerCase();
  const locationLower = (job.location || "").toLowerCase();
  const profileTitle = (profile.titre || "").toLowerCase();
  const profileLocation = (profile.ville || "").toLowerCase();

  if (profileTitle && titleLower.includes(profileTitle)) score += 70;
  else if (profileTitle) {
    const words = profileTitle.split(" ");
    const matched = words.filter(w => w.length > 3 && titleLower.includes(w));
    if(words.length > 0) score += (matched.length / words.length) * 50;
  }
  if (profileLocation && locationLower.includes(profileLocation)) score += 30;
  return Math.min(100, Math.round(score));
}

function JobCard({ job, profile, index }) {
  const score = job._score !== undefined ? job._score : computeScore(job, profile);
  const skills = (job.skills || "").split(",").map(s => s.trim()).filter(Boolean);
  const date = job.date_posted ? new Date(job.date_posted).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : null;
  const scoreColor = score >= 70 ? "#00d4aa" : score >= 40 ? "#6c63ff" : "#7a7a9a";
  
  const validUrl = job.job_url && !job.job_url.startsWith('http') 
      ? `https://${job.job_url}` 
      : job.job_url;

  // NEW: Function to open the link when ANY part of the card is clicked
  const handleCardClick = () => {
    if (validUrl) {
      window.open(validUrl, "_blank", "noopener,noreferrer");
    }
  };

  return (
    // NEW: Added the onClick handler to the main wrapper
    <div className="job-card" style={{ animationDelay: `${index * 0.05}s` }} onClick={handleCardClick}>
      <div className="job-card-top">
        <div style={{ flex: 1 }}>
          <div className="job-title">{job.title_raw || job.title}</div>
          <div className="job-company">{job.company || "Entreprise non précisée"}</div>
          {job.category && <span className="cat-chip">{job.category}</span>}
        </div>
        <div className="job-score" style={{ borderColor: `${scoreColor}30`, background: `${scoreColor}10` }}>
          <div className="job-score-num" style={{ color: scoreColor }}>{score}%</div>
          <div className="job-score-label">Match</div>
        </div>
      </div>
      <div className="match-bar">
        <div className="match-bar-fill" style={{ width: `${score}%`, background: `linear-gradient(90deg, ${scoreColor}, ${scoreColor}88)` }} />
      </div>
      <div className="job-meta">
        {job.location && <span className="job-meta-item">📍 {job.location}</span>}
        {date && <span className="job-meta-item">📅 {date}</span>}
        {job.contract_type && <span className="job-meta-item">📋 {job.contract_type}</span>}
        {job.salary && <span className="job-meta-item">💰 {job.salary}</span>}
      </div>
      {skills.length > 0 && (
        <div className="job-skills">
          {skills.slice(0, 6).map((s, i) => <span key={i} className="skill-badge">{s}</span>)}
          {skills.length > 6 && <span className="skill-badge">+{skills.length - 6}</span>}
        </div>
      )}
      <div className="job-footer">
        <span className={`source-badge ${job.source}`}>
          {job.source === "linkedin" ? "LinkedIn" : "France Travail"}
        </span>
        
        {/* NEW: Changed from <a> to <span> since the parent div handles the click now */}
        {job.job_url && (
          <span className="job-link">Voir l'offre →</span>
        )}
      </div>
    </div>
  );
}

function LoadingState({ step }) {
  const steps = [
    "Lecture et extraction de votre CV...",
    "Calcul de la correspondance sémantique...",
    "Sauvegarde de l'analyse et tri des résultats...",
  ];
  return (
    <div className="loading-state">
      <div className="loader" />
      <div className="loading-text">Recherche en cours</div>
      <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
        Notre IA analyse votre CV et recherche les meilleures opportunités
      </p>
      <div className="loading-steps">
        {steps.map((s, i) => (
          <div key={i} className={`loading-step ${i < step ? "done" : i === step ? "active" : ""}`}>
            {i < step ? "✓" : i === step ? "⟳" : "○"} {s}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────

export default function App() {
  const [theme, setTheme] = useState("light");
  const [view, setView] = useState("hero"); // hero | form | loading | results | auth | marketStats
  const [loadStep, setLoadStep] = useState(0);
  const [activeFilter, setActiveFilter] = useState("Tous");

  // Market dashboard states
  const [marketStats, setMarketStats] = useState(null);
  const [marketSkills, setMarketSkills] = useState([]);
  const [marketTimeline, setMarketTimeline] = useState([]);
  const [marketLayers, setMarketLayers] = useState({});
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState(null);
  const [marketLoaded, setMarketLoaded] = useState(false);

  // Auth states
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login"); // login | register
  const [authForm, setAuthForm] = useState({ firstName: "", lastName: "", email: "", password: "", confirmPassword: "" });
  const [showPassword, setShowPassword] = useState(false); // NEW STATE FOR PASSWORD TOGGLE

  const [profile, setProfile] = useState({ titre: "", ville: "", cv: null });
  const [profileError, setProfileError] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  // Initialize theme & session
  useEffect(() => {
    document.body.setAttribute("data-theme", theme);
    checkSession();
  }, [theme]);

  useEffect(() => {
    fetch(`${API_BASE}/stats`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  // Session Management
  const checkSession = () => {
    const sessionStr = localStorage.getItem("ji_session");
    if (sessionStr) {
      const session = JSON.parse(sessionStr);
      if (Date.now() - session.timestamp < SESSION_DURATION) {
        setUser(session.user);
        loadSavedAnalysis(session.user.id);
      } else {
        handleLogout();
      }
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authForm.email, password: authForm.password })
      });
      if (!res.ok) throw new Error("Identifiants incorrects ou API manquante.");
      
      const data = await res.json();
      const sessionData = { user: data.user, timestamp: Date.now() };
      localStorage.setItem("ji_session", JSON.stringify(sessionData));
      setUser(data.user);
      loadSavedAnalysis(data.user.id);
      setView("form");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);
    if (authForm.password !== authForm.confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(authForm)
      });
      if (!res.ok) throw new Error("Erreur lors de la création du compte ou API manquante.");
      
      const data = await res.json();
      const sessionData = { user: data.user, timestamp: Date.now() };
      localStorage.setItem("ji_session", JSON.stringify(sessionData));
      setUser(data.user);
      setView("form");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("ji_session");
    setUser(null);
    setJobs([]);
    setView("hero");
  };

  const loadSavedAnalysis = async (userId) => {
    try {
      const res = await fetch(`${API_BASE}/analysis/${userId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.jobs && data.jobs.length > 0) {
          setJobs(data.jobs);
          setProfile(data.profile);
        }
      }
    } catch (e) { console.log("Pas d'analyse sauvegardée."); }
  };

  const loadMarketDashboard = async (force = false) => {
    if (marketLoaded && !force) return;

    setMarketLoading(true);
    setMarketError(null);

    const fetchJson = async (url, fallback) => {
      try {
        const res = await fetch(url);
        if (!res.ok) return fallback;
        return await res.json();
      } catch {
        return fallback;
      }
    };

    try {
      const [statsData, skillsData, timelineData, layersData] = await Promise.all([
        fetchJson(`${API_BASE}/stats`, null),
        fetchJson(`${API_BASE}/stats/skills?limit=12`, { skills: [] }),
        fetchJson(`${API_BASE}/stats/timeline`, { timeline: [] }),
        fetchJson(`${API_BASE}/layers`, { layers: {} }),
      ]);

      if (!statsData) {
        throw new Error("Impossible de joindre l'API (http://localhost:8000). Vérifiez que le backend est démarré.");
      }

      setMarketStats(statsData);
      setMarketSkills(skillsData.skills || []);
      setMarketTimeline((timelineData.timeline || []).slice(0, 15));
      setMarketLayers(layersData.layers || {});
      setMarketLoaded(true);
    } catch (err) {
      setMarketError(err.message || "Erreur lors du chargement du dashboard.");
    } finally {
      setMarketLoading(false);
    }
  };

  const goToMarketStats = () => {
    setView("marketStats");
    loadMarketDashboard();
  };

  const toggleTheme = () => setTheme(prev => prev === "dark" ? "light" : "dark");
  const updateProfile = (key, val) => {
    setProfileError(null);
    setProfile(p => ({ ...p, [key]: val }));
  };

  const handleSubmit = async () => {
    if (!profile.cv && !profile.titre.trim()) {
      setProfileError("Veuillez renseigner un titre de poste ou importer votre CV.");
      return;
    }

    setProfileError(null);
    setView("loading");
    setLoadStep(0);

    try {
      setLoadStep(1); 
      const formData = new FormData();
      formData.append("title", profile.titre);
      formData.append("location", profile.ville);
      if (profile.cv) formData.append("cv", profile.cv);
      if (user) formData.append("user_id", user.id); // Send user ID to save the analysis

      const response = await fetch(`${API_BASE}/recommend`, {
        method: 'POST',
        body: formData, 
      });

      if (!response.ok) throw new Error("Erreur serveur API");
      
      setLoadStep(2); 
      const data = await response.json();

      setLoadStep(3); 
      await new Promise(r => setTimeout(r, 400)); 

      const scoredJobs = (data.jobs || []).map(job => ({ ...job, _score: job.score }));
      setJobs(scoredJobs);
      setView("results");
    } catch (err) {
      setError("Erreur de connexion avec l'API NLP. Vérifiez que votre backend est bien lancé sur le port 8000.");
      setView("form");
    }
  };

  const categories = ["Tous", ...new Set(jobs.map(j => j.category).filter(Boolean))];
  const filteredJobs = activeFilter === "Tous" ? jobs : jobs.filter(j => j.category === activeFilter);

  const navigateToProfile = () => {
    if (user) {
      setView("form");
    } else {
      setView("auth");
    }
  };

  return (
    <>
      <style>{styles}</style>
      <nav>
        <div className="nav-logo" onClick={() => setView("hero")} style={{ cursor: "pointer" }}>Job<span>Intelligent</span></div>
        <div className="nav-right">
          <ul className="nav-steps">
            <li className={view === "hero" ? "active" : ""} onClick={() => setView("hero")}>Accueil</li>
            <li className={view === "marketStats" ? "active" : ""} onClick={goToMarketStats}>Marché</li>
            <li className={view === "form" || view === "auth" ? "active" : ""} onClick={navigateToProfile}>Mon profil</li>
            {jobs.length > 0 && <li className={view === "results" ? "active" : ""} onClick={() => setView("results")}>Résultats</li>}
          </ul>
          {user && (
            <button className="logout-btn" onClick={handleLogout}>Déconnexion</button>
          )}
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "☀️ Mode Clair" : "🌙 Mode Sombre"}
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      {view === "hero" && (
        <div className="hero">
          <div className="hero-glow" />
          <span className="hero-tag">Propulsé par l'IA sémantique</span>
          <h1>Trouvez l'emploi<br /><em>fait pour vous</em></h1>
          <p className="hero-sub">
            Importez votre CV et notre système d'analyse sémantique identifie
            les offres les plus pertinentes parmi des centaines d'opportunités.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={navigateToProfile}>Analyser mon CV →</button>
            <button className="btn-secondary" onClick={goToMarketStats}>En savoir plus</button>
          </div>

          {stats && (
            <div className="stats-bar" id="stats">
              <div className="stat-item">
                <div className="stat-num">{stats.total_jobs?.toLocaleString("fr-FR") || "—"}</div>
                <div className="stat-label">Offres indexées</div>
              </div>
              <div className="stat-item">
                <div className="stat-num">{stats.by_source?.length || 2}</div>
                <div className="stat-label">Sources</div>
              </div>
              <div className="stat-item">
                <div className="stat-num">{stats.by_category?.length || "—"}</div>
                <div className="stat-label">Catégories</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── AUTHENTICATION ── */}
      {view === "auth" && (
        <section>
          <div className="auth-box">
            <h2>{authMode === "login" ? "Connexion" : "Créer un compte"}</h2>
            <p className="section-desc" style={{ marginBottom: "1.5rem" }}>
              {authMode === "login" ? "Accédez à vos analyses sauvegardées." : "Rejoignez-nous pour sauvegarder vos matchs."}
            </p>

            {error && (
              <div style={{ background: "rgba(255,107,107,0.1)", border: "1px solid rgba(255,107,107,0.3)", borderRadius: 10, padding: "1rem", marginBottom: "1.5rem", color: "#ff8c8c", fontSize: "0.9rem" }}>
                Erreur: {error}
              </div>
            )}

            <form className="form-grid" onSubmit={authMode === "login" ? handleLogin : handleRegister}>
              {authMode === "register" && (
                <div className="form-row">
                  <div className="field">
                    <label>Prénom</label>
                    <input type="text" placeholder="Ex: Khalil" required onChange={e => setAuthForm({...authForm, firstName: e.target.value})} />
                  </div>
                  <div className="field">
                    <label>Nom</label>
                    <input type="text" placeholder="Hamimid" required onChange={e => setAuthForm({...authForm, lastName: e.target.value})} />
                  </div>
                </div>
              )}
              <div className="field">
                <label>Adresse Email</label>
                <input type="email" placeholder="khalil@ensah.ma" required onChange={e => setAuthForm({...authForm, email: e.target.value})} />
              </div>

              {/* CHAMPS MOT DE PASSE MODIFIÉS */}
              <div className="field">
                <label>Mot de passe</label>
                <div className="password-wrapper">
                  <input 
                    type={showPassword ? "text" : "password"} 
                    placeholder="••••••••" 
                    required 
                    onChange={e => setAuthForm({...authForm, password: e.target.value})} 
                  />
                  <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? "Masquer" : "Afficher"}
                  </button>
                </div>
              </div>

              {authMode === "register" && (
                <div className="field">
                  <label>Confirmer le mot de passe</label>
                  <div className="password-wrapper">
                    <input 
                      type={showPassword ? "text" : "password"} 
                      placeholder="••••••••" 
                      required 
                      onChange={e => setAuthForm({...authForm, confirmPassword: e.target.value})} 
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? "Masquer" : "Afficher"}
                    </button>
                  </div>
                </div>
              )}
              
              <button type="submit" className="btn-primary" style={{ marginTop: "1rem", width: "100%", justifyContent: "center" }}>
                {authMode === "login" ? "Se connecter" : "Créer le compte"}
              </button>
            </form>

            <div className="auth-toggle">
              {authMode === "login" ? (
                <>Pas encore de compte ? <span onClick={() => { setAuthMode("register"); setError(null); }}>S'inscrire</span></>
              ) : (
                <>Déjà un compte ? <span onClick={() => { setAuthMode("login"); setError(null); }}>Se connecter</span></>
              )}
            </div>
          </div>
        </section>
      )}

      {/* ── FORM (Requires Auth) ── */}
      {view === "form" && user && (
        <section>
          <div className="section-label">Bonjour, {user.firstName}</div>
          <h2>Votre profil</h2>
          <p className="section-desc">
            Plus votre CV est détaillé, plus les recommandations seront précises.
          </p>

          {jobs.length > 0 && (
            <div style={{ background: "rgba(108,99,255,0.08)", border: "1px solid rgba(108,99,255,0.2)", borderRadius: 10, padding: "1rem 1.2rem", marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ color: "var(--accent)" }}>Une analyse précédente a été trouvée.</strong>
                <p style={{ fontSize: "0.85rem", color: "var(--muted)", margin: 0 }}>Voulez-vous consulter vos résultats sauvegardés ?</p>
              </div>
              <button className="btn-primary" style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }} onClick={() => setView("results")}>
                Voir les résultats
              </button>
            </div>
          )}

          {error && (
            <div style={{ background: "rgba(255,107,107,0.1)", border: "1px solid rgba(255,107,107,0.3)", borderRadius: 10, padding: "1rem 1.2rem", marginBottom: "1.5rem", color: "#ff8c8c", fontSize: "0.9rem" }}>
              Erreur: {error}
            </div>
          )}

          {profileError && (
            <div style={{ background: "rgba(255,107,107,0.1)", border: "1px solid rgba(255,107,107,0.3)", borderRadius: 10, padding: "1rem 1.2rem", marginBottom: "1.5rem", color: "#ff8c8c", fontSize: "0.9rem" }}>
              Validation: {profileError}
            </div>
          )}

          <div className="form-grid">
            <div className="form-row">
              <div className="field">
                <label>Titre de poste recherché *</label>
                <input type="text" placeholder="Data Engineer, ML Engineer..." value={profile.titre} onChange={e => updateProfile("titre", e.target.value)} />
              </div>
              <div className="field">
                <label>Ville souhaitée</label>
                <input type="text" placeholder="Meknès, Casablanca..." value={profile.ville} onChange={e => updateProfile("ville", e.target.value)} />
              </div>
            </div>

            <div className="field" style={{ marginTop: "1rem" }}>
              <label>Votre CV (PDF)</label>
              <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "0.5rem" }}>
                Notre IA va extraire vos compétences et expériences directement depuis votre CV.
              </p>
              {profile.cv ? (
                <div className="cv-uploaded">
                  <span className="cv-uploaded-icon">CV</span>
                  <div>
                    <div className="cv-uploaded-name">{profile.cv.name}</div>
                    <div className="cv-uploaded-size">{(profile.cv.size / 1024).toFixed(0)} Ko</div>
                  </div>
                  <button className="cv-remove" onClick={() => updateProfile("cv", null)} aria-label="Supprimer le CV">Retirer</button>
                </div>
              ) : (
                <label className="cv-drop">
                  <input type="file" accept=".pdf" onChange={e => updateProfile("cv", e.target.files[0] || null)} />
                  <div className="cv-icon">CV</div>
                  <p><strong>Glissez votre CV</strong> ou cliquez pour parcourir</p>
                  <p style={{ fontSize: "0.8rem", marginTop: "0.3rem" }}>Format PDF uniquement</p>
                </label>
              )}
            </div>
          </div>

          <div className="form-actions">
            <button className="btn-secondary" onClick={() => setView("hero")}>← Retour</button>
            <button className="btn-primary" onClick={handleSubmit}>Lancer une nouvelle analyse →</button>
          </div>
        </section>
      )}

      {/* ── MARKET DASHBOARD ── */}
      {view === "marketStats" && (
        <section>
          <div className="dashboard-shell">
            <div className="dashboard-hero">
              <div>
                <div className="section-label" style={{ marginBottom: "0.45rem" }}>Insights marché</div>
                <h2>Tableau de bord du marché</h2>
                <p className="section-desc" style={{ marginBottom: 0 }}>
                  Statistiques en temps réel basées sur les offres indexées dans la base.
                </p>
              </div>
              <button className="btn-secondary" onClick={() => loadMarketDashboard(true)}>Actualiser</button>
            </div>

            {marketLoading ? (
              <div className="dashboard-section">
                <div className="loading-state" style={{ padding: "2.2rem 1rem" }}>
                  <div className="loader" />
                  <div className="loading-text">Chargement des statistiques...</div>
                </div>
              </div>
            ) : marketError ? (
              <div className="dashboard-section" style={{ borderColor: "rgba(255,107,107,0.35)", background: "rgba(255,107,107,0.06)" }}>
                <div style={{ color: "#ff8c8c", fontSize: "0.92rem" }}>⚠️ {marketError}</div>
                <div style={{ marginTop: "0.85rem" }}>
                  <button className="btn-secondary" onClick={() => loadMarketDashboard(true)}>Réessayer</button>
                </div>
              </div>
            ) : marketStats ? (
              <>
                <div className="dashboard-kpi-grid">
                  <div className="kpi-card">
                    <div className="kpi-value">{marketStats.total_jobs?.toLocaleString("fr-FR") || "—"}</div>
                    <div className="kpi-label">Offres totales</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-value">{(marketStats.by_source?.length || 0).toLocaleString("fr-FR")}</div>
                    <div className="kpi-label">Sources actives</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-value">{(marketStats.by_category?.length || 0).toLocaleString("fr-FR")}</div>
                    <div className="kpi-label">Catégories</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-value" style={{ fontSize: "1.15rem" }}>{marketStats.top_locations?.[0]?.location || "—"}</div>
                    <div className="kpi-label">Top localisation</div>
                  </div>
                </div>

                <div className="dashboard-grid-2">
                  <div className="dashboard-section">
                    <div className="dashboard-section-head">
                      <div className="dashboard-title">Métiers les plus fréquents</div>
                    </div>
                    <div className="dashboard-list">
                      {(marketStats.top_titles || []).slice(0, 8).map((row, i) => (
                        <div key={i} className="dashboard-list-item">
                          <div className="dashboard-item-main">{row.title || "Non précisé"}</div>
                          <div className="dashboard-count-pill">{(row.count || 0).toLocaleString("fr-FR")} offres</div>
                        </div>
                      ))}
                      {(!marketStats.top_titles || marketStats.top_titles.length === 0) && (
                        <div className="dashboard-list-item">
                          <div className="timeline-cell">Aucune donnée disponible.</div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="dashboard-section">
                    <div className="dashboard-section-head">
                      <div className="dashboard-title">Compétences les plus demandées</div>
                    </div>
                    <div className="dashboard-chip-cloud">
                      {marketSkills.map((s, i) => (
                        <span key={i} className="dashboard-chip">{s.skill} ({(s.count || 0).toLocaleString("fr-FR")})</span>
                      ))}
                      {marketSkills.length === 0 && <span className="dashboard-chip">Aucune donnée disponible</span>}
                    </div>
                  </div>
                </div>

                <div className="dashboard-section">
                  <div className="dashboard-section-head">
                    <div className="dashboard-title">Activité récente</div>
                  </div>
                  <div className="timeline-table">
                    {marketTimeline.map((t, i) => (
                      <div key={i} className="timeline-row">
                        <div className="timeline-cell"><strong>{t.date_posted || "N/A"}</strong></div>
                        <div className="timeline-cell">{t.source || "N/A"}</div>
                        <div className="dashboard-count-pill">{(t.count || 0).toLocaleString("fr-FR")} offres</div>
                      </div>
                    ))}
                    {marketTimeline.length === 0 && (
                      <div className="timeline-row">
                        <div className="timeline-cell"><strong>Aucune activité</strong></div>
                        <div className="timeline-cell">—</div>
                        <div className="dashboard-count-pill">0</div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="dashboard-section">
                  <div className="dashboard-section-head">
                    <div className="dashboard-title">Couches Medallion</div>
                  </div>
                  <div className="layer-grid">
                    {Object.entries(marketLayers).map(([layer, count]) => (
                      <div key={layer} className="layer-card">
                        <div className="layer-name">{layer}</div>
                        <div className="layer-value">{typeof count === "number" ? count.toLocaleString("fr-FR") : String(count)}</div>
                      </div>
                    ))}
                    {Object.keys(marketLayers).length === 0 && (
                      <div className="layer-card">
                        <div className="layer-name">Aucune couche</div>
                        <div className="layer-value">—</div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </section>
      )}

      {/* ── LOADING ── */}
      {view === "loading" && <LoadingState step={loadStep} />}

      {/* ── RESULTS ── */}
      {view === "results" && (
        <section>
          <div className="section-label">Étape 2 / 2 — Résultats</div>
          <div className="results-header">
            <div>
              <h2>Vos opportunités</h2>
              <div className="results-count">
                <strong>{filteredJobs.length}</strong> offres correspondant à votre profil
              </div>
            </div>
            <button className="btn-secondary" onClick={() => { setView("form"); setError(null); }}>← Revenir au profil</button>
          </div>

          {categories.length > 1 && (
            <div className="filters">
              {categories.map(cat => (
                <button key={cat} className={`filter-btn ${activeFilter === cat ? "active" : ""}`} onClick={() => setActiveFilter(cat)}>
                  {cat} <span style={{ marginLeft: "0.3rem", opacity: 0.6 }}>({cat === "Tous" ? jobs.length : jobs.filter(j => j.category === cat).length})</span>
                </button>
              ))}
            </div>
          )}

          {filteredJobs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>Aucune offre trouvée pour ce profil.</p>
              <p style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>Essayez d'élargir vos critères.</p>
            </div>
          ) : (
            <div className="jobs-grid">
              {filteredJobs.map((job, i) => <JobCard key={job.id || i} job={job} profile={profile} index={i} />)}
            </div>
          )}
        </section>
      )}
    </>
  );
}