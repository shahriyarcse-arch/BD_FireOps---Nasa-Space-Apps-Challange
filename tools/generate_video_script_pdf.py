"""
Generate BD-FireOps Video Presentation Script PDF (Bilingual: English + Bengali)
Uses headless Edge to print a beautifully styled, high-resolution A4 PDF.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_OUT = ROOT / "tools" / "video_script_template.html"
PDF_OUT = ROOT / "BD_FireOps_Video_Presentation_Script.pdf"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BD-FireOps — 4-Minute Video Presentation Script (Bilingual)</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Hind+Siliguri:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

    @page {
      size: A4 portrait;
      margin: 8mm 10mm 8mm 10mm;
      @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5pt;
        color: #64748b;
      }
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #0f172a;
      background: #ffffff;
      line-height: 1.45;
      font-size: 9pt;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    .bn {
      font-family: 'Hind Siliguri', 'Kalpurush', 'Vrinda', 'Nirmala UI', sans-serif;
      line-height: 1.48;
    }

    /* HEADER BANNER */
    .header-banner {
      background: linear-gradient(135deg, #070d1e 0%, #0f172a 100%);
      color: #ffffff;
      padding: 10px 14px;
      border-radius: 6px;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border: 1px solid #1e293b;
    }

    .header-title h1 {
      font-size: 13pt;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .header-title p {
      font-size: 8pt;
      color: #94a3b8;
      margin-top: 1px;
    }

    .header-badges {
      text-align: right;
    }

    .badge {
      display: inline-block;
      padding: 3px 7px;
      border-radius: 4px;
      font-size: 7pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-family: 'JetBrains Mono', monospace;
    }

    .badge-nasa {
      background: #0284c7;
      color: #ffffff;
    }

    .badge-time {
      background: #f59e0b;
      color: #0f172a;
      margin-left: 4px;
    }

    /* QUICK CHEAT SHEET */
    .cheat-sheet {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 6px 10px;
      margin-bottom: 8px;
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 4px;
      text-align: center;
    }

    .cheat-item .label {
      font-size: 6.5pt;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.02em;
    }

    .cheat-item .val {
      font-size: 9.5pt;
      font-weight: 800;
      color: #0f172a;
      font-family: 'JetBrains Mono', monospace;
    }

    .cheat-item .highlight {
      color: #0284c7;
    }

    /* SCENE CARDS */
    .scene-card {
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      margin-bottom: 8px;
      overflow: hidden;
      page-break-inside: avoid;
      background: #ffffff;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }

    .scene-header {
      background: #0f172a;
      color: #f8fafc;
      padding: 5px 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #38bdf8;
    }

    .scene-header .title {
      font-size: 9pt;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .scene-header .timing {
      font-family: 'JetBrains Mono', monospace;
      font-size: 7.5pt;
      color: #38bdf8;
      font-weight: 700;
      background: rgba(56, 189, 248, 0.12);
      padding: 2px 6px;
      border-radius: 3px;
    }

    .action-box {
      background: #f1f5f9;
      border-bottom: 1px solid #e2e8f0;
      padding: 5px 10px;
      display: flex;
      align-items: flex-start;
      gap: 6px;
      font-size: 7.8pt;
      color: #334155;
    }

    .action-badge {
      background: #dc2626;
      color: #ffffff;
      font-weight: 800;
      padding: 1px 4px;
      border-radius: 3px;
      font-size: 6pt;
      text-transform: uppercase;
      white-space: nowrap;
      margin-top: 1px;
    }

    .action-text {
      flex: 1;
      font-weight: 600;
    }

    .script-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    .script-col {
      padding: 8px 10px;
    }

    .script-col.en {
      border-right: 1px solid #e2e8f0;
      background: #ffffff;
    }

    .script-col.bn {
      background: #fbfcfe;
    }

    .lang-tag {
      font-size: 6.5pt;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 3px;
      display: inline-block;
      padding: 1px 4px;
      border-radius: 2px;
    }

    .lang-tag.en {
      background: #e0f2fe;
      color: #0369a1;
    }

    .lang-tag.bn {
      background: #fef3c7;
      color: #92400e;
    }

    .speech-text {
      font-size: 8.5pt;
      color: #0f172a;
      line-height: 1.45;
    }

    .speech-text strong {
      color: #0369a1;
      font-weight: 700;
    }

    /* TIPS AND VOCABULARY BOX */
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 6px;
      page-break-inside: avoid;
    }

    .info-card {
      border-radius: 6px;
      padding: 7px 10px;
      font-size: 7.8pt;
    }

    .tips-card {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
    }

    .tips-card h4 {
      font-weight: 800;
      font-size: 8.2pt;
      margin-bottom: 3px;
      color: #15803d;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .vocab-card {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
    }

    .vocab-card h4 {
      font-weight: 800;
      font-size: 8.2pt;
      margin-bottom: 3px;
      color: #1d4ed8;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .vocab-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 3px 6px;
      margin-top: 3px;
    }

    .vocab-item {
      font-size: 7.2pt;
      line-height: 1.35;
    }

    .vocab-item code {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      color: #0369a1;
    }

    .page-break {
      page-break-after: always;
    }
  </style>
</head>
<body>

  <!-- ==================== PAGE 1 ==================== -->
  <div class="header-banner">
    <div class="header-title">
      <h1>🚀 BD-FireOps &middot; Presentation Teleprompter</h1>
      <p>NASA Space Apps Challenge 2026 &bull; 4-Minute (240-Second) Video Walkthrough Script</p>
    </div>
    <div class="header-badges">
      <span class="badge badge-nasa">NASA Challenge</span>
      <span class="badge badge-time">4 Min Max</span>
    </div>
  </div>

  <!-- QUICK NUMBERS CHEAT SHEET -->
  <div class="cheat-sheet">
    <div class="cheat-item">
      <div class="label">RMSE Drop</div>
      <div class="val highlight">-95.1%</div>
    </div>
    <div class="cheat-item">
      <div class="label">Test RMSE</div>
      <div class="val">55.67</div>
    </div>
    <div class="cheat-item">
      <div class="label">Mean Bias</div>
      <div class="val">-4.09</div>
    </div>
    <div class="cheat-item">
      <div class="label">Held-out R²</div>
      <div class="val highlight">0.9811</div>
    </div>
    <div class="cheat-item">
      <div class="label">Sensor Shift</div>
      <div class="val">2.85× (+185%)</div>
    </div>
    <div class="cheat-item">
      <div class="label">Bootstrap CI</div>
      <div class="val">[0.2198, 0.2970]</div>
    </div>
  </div>

  <!-- SCENE 1 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 1 &middot; Introduction & The 2026 Impending Crisis</div>
      <div class="timing">⏱️ 0:00 – 0:35 (35 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">ব্রাউজারে <code>index.html</code> ওপেন রাখুন। টপবারের NASA লোগো, ডার্ক/লাইট মোড বাটন একবার টগল করুন এবং চারটি টেলিমেট্রি চিপস (Coverage 2002-2021, Overlap 84 mo, Model OLS, RMSE -95.1%) মাউস দিয়ে নির্দেশ করুন।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "Hello judges and Earth observation community! We are <strong>Team Claude Fable 7.0</strong> presenting <strong>BD-FireOps</strong>. NASA projects the end-of-science for Terra and Aqua MODIS in 2027, while NOAA has permanently ceased Suomi-NPP VIIRS delivery. Earth observation scientists face a critical data cliff. Over Bangladesh's Chittagong Hill Tracts, directly merging MODIS and VIIRS records creates an alarming, artificial jump. We built an uncertainty-quantified, held-out validated harmonization engine that turns two incompatible sensors into one continuous, 20-year climate record."
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "আসসালামু আলাইকুম এবং হ্যালো বিচারকমণ্ডলী! আমরা <strong>টিম ক্লদ ফেবল ৭.০</strong> উপস্থাপন করছি <strong>বিডি-ফায়ারঅপস (BD-FireOps)</strong>। ২০২৭ সালের মধ্যে নাসার ঐতিহাসিক টেরা ও অ্যাকোয়া মোডিস স্যাটেলাইট বিদায় নিচ্ছে এবং নোয়া (NOAA) সুওমি-এনপিপি ভিয়ার্স ডেটা স্থায়ীভাবে বন্ধ করেছে। ফলে দীর্ঘমেয়াদী জলবায়ু পর্যালোচনার জন্য মোডিস এবং ভিয়ার্স সরাসরি জোড়া দিলে তৈরি হয় এক মারাত্মক ডেটা বিভ্রাট। বাংলাদেশের পার্বত্য চট্টগ্রামের বনাঞ্চলে এই ডেটা সংকট নিরসনে আমরা তৈরি করেছি সায়েন্টিফিকালি ভেরিফায়েড এবং আনসার্টেইনটি-কোয়ান্টিফায়েড হারমোনাইজেশন সিস্টেম।"
        </p>
      </div>
    </div>
  </div>

  <!-- SCENE 2 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 2 &middot; The Problem & Dual-View Time Series</div>
      <div class="timing">⏱️ 0:35 – 1:15 (40 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">স্ক্রোল করে "The Problem" সেকশনে যান। Chart A-এর নিচে লাল ওয়ার্নিং ব্যাজ (+185% / 2.85×) হোভার করুন। এরপর উপরে "Chart View Switcher" বাটনে ক্লিক করে "Continuous Harmonized" ভিউতে সুইচ করে Chart B এর স্মুথ কার্ভ দেখান।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "Take a look at this raw splice. From 2002 to 2011, Aqua MODIS recorded an average of <strong>207 fire hotspots</strong> a month. But in 2012, when 375-meter VIIRS takes over, the mean count explodes to <strong>590</strong> — an artificial <strong>2.85-times jump</strong> at the splice, and <strong>3.71-times</strong> during overlapping months! The forest didn't suddenly catch fire three times more — only the satellite's spatial sensitivity changed. Watch what happens when I toggle to our <strong>Harmonized View</strong>: BD-FireOps removes this artificial step completely, providing 20 years of continuous, jump-free telemetry."
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "স্ক্রিনে অপরিবর্তিত র' ডেটা খেয়াল করুন। ২০০২ থেকে ২০১১ পর্যন্ত অ্যাকোয়া মোডিস মাসে গড়ে <strong>২০৭টি হটস্পট</strong> রেকর্ড করেছিল। কিন্তু ২০১২ সালে উচ্চ রেজোলিউশনের ৩৭৫-মিটার ভিয়ার্স আসতেই মাসিক গড় লাফিয়ে দাঁড়ায় <strong>৫৯০-এ</strong>—যা প্রায় <strong>২.৮৫ গুণ বা ১৮৫% কৃত্রিম বৃদ্ধি</strong>! বাস্তবে বনে আগুন তিনগুণ বাড়েনি, কেবল ক্যামেরার রেজোলিউশন বদলেছে। এবার আমাদের 'Continuous Harmonized View' বাটনে ক্লিক করলেই দেখতে পাবেন—বিডি-ফায়ারঅপস কীভাবে এই কৃত্রিম জাম্প দূর করে ২০ বছরের নিরবচ্ছিন্ন এবং বাস্তবসম্মত টাইম-সিরিজ উপহার দেয়।"
        </p>
      </div>
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ==================== PAGE 2 ==================== -->
  <!-- SCENE 3 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 3 &middot; Scientific Proof & 3-Year Held-Out Validation</div>
      <div class="timing">⏱️ 1:15 – 1:55 (40 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">স্ক্রোল করে "Proof" সেকশনে যান। বড় ৩টি KPI কার্ডে মাউস পয়েন্ট করুন: <strong>RMSE 55.67</strong>, <strong>Bias -4.09</strong>, এবং <strong>R² 0.9811</strong>। নিচে প্রতি বছরের ভ্যালিডেশন টেবিল (2019, 2020, 2021) এবং বুটস্ট্র্যাপ ফর্মুলা দেখান।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "How do we prove this works? We trained our calibration strictly on 2012 to 2018, and validated it on three completely untouched held-out years: 2019 through 2021. The results are decisive: prediction error plunged by <strong>95.1%</strong>, dropping RMSE from 1,130 down to <strong>55.67 hotspots</strong> per month. Mean sensor bias dropped by <strong>99.1%</strong> from plus 469 to just <strong>−4.09</strong>, reaching an outstanding <strong>R² of 0.9811</strong> on unseen months. Our 500-sample moving-block bootstrap establishes a robust 95% confidence interval of <strong>0.2198 to 0.2970</strong>."
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "আমাদের মডেল কতটা নিখুঁত? আমরা ২০১২ থেকে ২০১৮ সাল পর্যন্ত ডেটা দিয়ে মডেল ট্রেইন করেছি এবং ২০১৯ থেকে ২০২১—এই সম্পূর্ণ অদেখা ৩টি বছরের ডেটার ওপর টেস্ট করেছি। ফলাফল দেখুন: মডেলের এরর বা RMSE <strong>৯৫.১% হ্রাস</strong> পেয়ে ১,১৩০ থেকে নেমে এসেছে মাত্র <strong>৫৫.৬৭-এ</strong>! সেন্সর বায়াস <strong>৯৯.১% কমে</strong> প্লাস ৪৬৯ থেকে নেমে এসেছে মাত্র <strong>মাইনাস ৪.০৯-এ</strong>, এবং অদেখা টেস্ট ডেটাতেও <strong>R² দাঁড়িয়েছে ০.৯৮১১</strong>। ৫০০ স্যাম্পলের মুভিং-ব্লক বুটস্ট্র্যাপের মাধ্যমে আমাদের ৯৫% কনফিডেন্স ইন্টারভাল সুনির্দিষ্টভাবে প্রমাণিত।"
        </p>
      </div>
    </div>
  </div>

  <!-- SCENE 4 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 4 &middot; Live Policy Simulator & Uncertainty Engine</div>
      <div class="timing">⏱️ 1:55 – 2:35 (40 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">"Live Scenario Simulator" কার্ডে যান। VIIRS স্লাইডারটি ড্র্যাগ করে <strong>৩০০-এ</strong> নিন (মোডিস আসবে ৭৯.৬)। এরপর Mitigation স্লাইডারটি টেনে <strong>-২০%</strong> করুন (রিজাল্ট নামবে ৬৩.৫-এ)। সাথে সাথে নিচে বুটস্ট্র্যাপ ইন্টারভাল বক্স <strong>[৫৯.১, ৯৫.৬]</strong> দেখান।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "BD-FireOps is not just an archive; it is an active decision-making console. Forestry and disaster officials can input any raw VIIRS count — say, <strong>300 detections</strong> — and our engine calculates that MODIS would have seen <strong>79.6</strong>. Policy makers can model wildfire mitigation: apply a <strong>20% intervention reduction</strong>, and the system dynamically updates the predicted baseline along with honest <strong>95% moving-block bootstrap uncertainty bounds</strong>. It provides empirical clarity, not guesswork."
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "বিডি-ফায়ারঅপস কেবল একটি আর্কাইভ নয়, এটি পলিসি প্ল্যানিংয়ের জন্য জীবন্ত টুল। বন অধিদপ্তর বা দুর্যোগ ব্যবস্থাপনা দল এখানে যেকোনো মাসের ভিয়ার্স ফায়ার কাউন্ট—যেমন <strong>৩০০</strong>—ইনপুট করলেই আমাদের ইঞ্জিন হিসাব করে দেবে যে মোডিস রিডিং হতো প্রায় <strong>৭৯.৬</strong>। শুধু তাই নয়, পাশের মিটিগেশন স্লাইডার দিয়ে <strong>২০% আগুন কমানোর পরিকল্পনা</strong> সেট করলেই সাথে সাথে প্রত্যাশিত আউটপুট এবং ৯৫% বুটস্ট্র্যাপ অনিশ্চয়তা পরিসীমা স্ক্রিনে রিয়েল-টাইমে আপডেট হয়।"
        </p>
      </div>
    </div>
  </div>

  <div class="page-break"></div>

  <!-- ==================== PAGE 3 ==================== -->
  <!-- SCENE 5 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 5 &middot; Web GIS Map & 20-Year Seasonality Matrix</div>
      <div class="timing">⏱️ 2:35 – 3:20 (45 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">ম্যাপে <strong>"Dark gray"</strong> এবং <strong>"Satellite"</strong> বেসম্যাপ টগল করুন। টাইমলাইনের <strong>"Play"</strong> বাটনে ক্লিক করে ২০০২ থেকে ২০২১ পর্যন্ত হটস্পট অ্যানিমেশন দেখান। এরপর নিচে <strong>"20-Year Seasonality Matrix"</strong>-এ স্ক্রোল করে মার্চ-এপ্রিলের পিক জুম সিজন দেখান।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "Now explore our Web GIS map. We strictly bounded detections using official geoBoundaries district polygons, filtering out over 140,000 fringe detections outside CHT borders. You can toggle between <strong>Esri High-Resolution Satellite</strong> and <strong>Esri Dark Gray</strong> basemaps. Watch as I press <strong>Play</strong> on our timeline scrubber — two decades of fire dynamics animate across Bandarban, Rangamati, and Khagrachhari. Below, our <strong>20-year seasonality matrix</strong> exposes the region's core rhythm: fire activity consistently peaks during the dry pre-monsoon <strong>March–April Jhum agricultural cycle</strong>."
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "এবার আমাদের ওয়েব জিআইএস (Web GIS) ম্যাপটি দেখুন। আমরা বান্দরবান, রাঙ্গামাটি ও খাগড়াছড়ির বাইরের ১ লাখ ৪০ হাজারের বেশি ডেটা ফিল্টার করেছি। ইউজার চাইলে সরাসরি <strong>এসরি স্যাটেলাইট</strong> বা <strong>ডার্ক বেসম্যাপে</strong> সুইচ করতে পারেন। টাইমলাইন স্ক্রাবারের <strong>Play বাটনে</strong> চাপ দিলেই বিগত ২০ বছরের আগুনের ভৌগোলিক পরিবর্তন চোখের সামনে অ্যানিমেটেড হয়ে ওঠে। আর নিচে আমাদের <strong>২০ বছরের সিজনালিটি ম্যাট্রিক্স</strong> স্পষ্ট প্রমাণ করে—প্রতি বছরই মার্চ-এপ্রিল মাসে ঐতিহ্যবাহী জুম চাষের মৌসুমে আগুনের তীব্রতা তুঙ্গে ওঠে।"
        </p>
      </div>
    </div>
  </div>

  <!-- SCENE 6 -->
  <div class="scene-card">
    <div class="scene-header">
      <div class="title">🎬 Scene 6 &middot; Scientific Integrity & Open Source Conclusion</div>
      <div class="timing">⏱️ 3:20 – 4:00 (40 sec)</div>
    </div>
    <div class="action-box">
      <span class="action-badge">ON-SCREEN ACTION</span>
      <span class="action-text">স্ক্রোল করে "Methodology" এবং "Honest Limitations" কার্ডে যান। সবশেষে ফুটারের GitHub লিংক এবং লাইভ ভেরিফিকেশন স্ট্যাটাস মাউস দিয়ে দেখিয়ে কনক্লুড করুন।</span>
    </div>
    <div class="script-grid">
      <div class="script-col en">
        <span class="lang-tag en">English (Read Exactly)</span>
        <p class="speech-text">
          "Finally, BD-FireOps maintains absolute scientific integrity. We are transparent: this is a regional empirical calibration for monthly climate trends — not a global converter, and not a live wildfire alarm. The entire architecture is <strong>100% open-source, client-side, zero-dependency</strong>, and verified by <strong>35 automated end-to-end tests</strong>. BD-FireOps bridges the gap between past and future NASA Earth observations. Thank you!"
        </p>
      </div>
      <div class="script-col bn">
        <span class="lang-tag bn">বাংলা (সহজ ও সাবলীল)</span>
        <p class="speech-text bn">
          "সর্বোপরি, বিডি-ফায়ারঅপস শতভাগ বৈজ্ঞানিক সততা মেনে তৈরি। আমরা স্পষ্টভাবে উল্লেখ করেছি—এটি পার্বত্য চট্টগ্রামের জন্য একটি রিজিওনাল এমপিরিকাল মডেল, কোনো গ্লোবাল কনভার্টার বা লাইভ অ্যালার্ম নয়। সম্পূর্ণ প্রজেক্টটি ওপেন-সোর্স, জিরো-ডিপেন্ডেন্সি এবং ৩৫টি অটোমেটেড টেস্ট দ্বারা শতভাগ ভেরিফায়েড। নাসার দুই দশকের আর্থ অবজারভেশনের ধারাবাহিকতা রক্ষায় বিডি-ফায়ারঅপস একটি বিশ্বস্ত সমাধান। সবাইকে আন্তরিক ধন্যবাদ!"
        </p>
      </div>
    </div>
  </div>

  <!-- PRO-TIPS AND PRONUNCIATION GUIDES -->
  <div class="info-grid">
    <div class="info-card tips-card">
      <h4>💡 Video Recording Pro-Tips</h4>
      <p>
        &bull; <strong>টুলস:</strong> Windows Game Bar (<code>Win + G</code>), OBS Studio, অথবা Loom ব্যবহার করুন (1080p Full HD)।<br>
        &bull; <strong>ভাষা:</strong> গ্লোবাল জাজদের জন্য <strong>ইংরেজি স্ক্রিপ্টটি হুবহু উচ্চারণ করা</strong> সবচেয়ে কার্যকর। লোকাল জাজ বা বাংলা ডাবিংয়ের জন্য পাশের <strong>বাংলা স্ক্রিপ্টটি</strong> একদম সাবলীল মুখে পড়ার জন্য তৈরি।<br>
        &bull; <strong>পেসিং:</strong> প্রতি সিন শেষ হলে ১ সেকেন্ড পজ দিন। ৪ মিনিট (২৪০ সেকেন্ড) পারফেক্ট সময়।
      </p>
    </div>

    <div class="info-card vocab-card">
      <h4>🗣️ Pronunciation & Acronym Guide</h4>
      <div class="vocab-grid">
        <div class="vocab-item"><code>MODIS</code> &rarr; <em>"MO-dis"</em> (মো-ডিস)</div>
        <div class="vocab-item"><code>VIIRS</code> &rarr; <em>"VEERZ"</em> (ভি-য়ার্স)</div>
        <div class="vocab-item"><code>Suomi-NPP</code> &rarr; <em>"SWOH-mee N-P-P"</em></div>
        <div class="vocab-item"><code>RMSE</code> &rarr; <em>"Root Mean Square Error"</em></div>
        <div class="vocab-item"><code>CHT</code> &rarr; <em>"Chittagong Hill Tracts"</em></div>
        <div class="vocab-item"><code>Jhum</code> &rarr; <em>"Jhoom"</em> (জুম চাষ)</div>
      </div>
    </div>
  </div>

</body>
</html>
"""

def generate_pdf():
    # Write HTML template
    HTML_OUT.write_text(HTML_CONTENT, encoding="utf-8")
    print(f"[HTML] Written template to {HTML_OUT}")

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge_bin = None
    for p in edge_paths:
        if os.path.exists(p):
            edge_bin = p
            break

    if not edge_bin:
        print("[ERROR] Microsoft Edge executable not found for PDF printing.")
        sys.exit(1)

    url = f"file:///{str(HTML_OUT).replace(os.sep, '/')}"
    cmd = [
        edge_bin,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(PDF_OUT)}",
        url
    ]

    print(f"[EDGE] Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and PDF_OUT.exists():
        size_kb = PDF_OUT.stat().st_size / 1024
        print(f"[SUCCESS] PDF generated successfully: {PDF_OUT} ({size_kb:.1f} KB)")
    else:
        print(f"[FAIL] Return code: {res.returncode}")
        print(f"Stderr: {res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
