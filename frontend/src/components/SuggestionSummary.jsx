import React, { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import {
  getCAOverall,
  getCADimension,
  getCASubthemeByFile,
} from "../api";

// ---------------------------------------------------------
// Detect type of payload
// ---------------------------------------------------------
function detectKind(p) {
  if (!p || typeof p !== "object") return "unknown";
  if (p.subtheme) return "subtheme";
  if (p.dimension) return "dimension";
  if (p.section && (p.section.executive_briefing || p.section.executiveBriefing || p.section.overview)) {
    return "overall";
  }
  if (p.top_subthemes) return "dimension";
  if (p.typical_contexts) return "subtheme";
  return "unknown";
}

// ---------------------------------------------------------
// Normalize payload
// ---------------------------------------------------------
function normalizePayload(payload) {
  if (!payload || typeof payload !== "object") return { title: "", sections: [] };

  const kind = detectKind(payload);

  // overall
  if (kind === "overall") {
    const sec = payload.section || {};
    const eb = sec.executive_briefing || sec.executiveBriefing || sec.overview || {};
    const counts = eb.sentiment_and_confidence?.counts || eb.counts || {};
    const avg = eb.sentiment_and_confidence?.average_confidence ?? eb.average_confidence;

    return {
      title: payload.report_title || payload.title || "Insights",
      sections: [
        {
          title: "Executive Briefing",
          type: "bullets",
          content: [
            ...(Array.isArray(eb.key_insights) ? eb.key_insights : []),
            ...(eb.title ? [String(eb.title)] : []),
          ],
        },
        {
          title: "Sentiment & Confidence",
          type: "sentiment",
          content: {
            summary: eb.sentiment_and_confidence?.summary || eb.summary || "",
            counts: {
              positive: counts.positive ?? 0,
              negative: counts.negative ?? 0,
              average_confidence: typeof avg === "number" ? avg : undefined,
            },
            overall: eb.sentiment_and_confidence?.overall_sentiment || eb.overall_sentiment || "",
          },
        },
        {
          title: "Risks & Opportunities",
          type: "riskopp",
          content: {
            risks: eb.risks_and_opportunities?.risks || eb.risks || [],
            opportunities: eb.risks_and_opportunities?.opportunities || eb.opportunities || [],
          },
        },
        {
          title: "Actionable Recommendations",
          type: "actions",
          content: eb.actionable_recommendations || eb.recommendations || [],
        },
      ],
    };
  }

  // dimension
  if (kind === "dimension") {
    const OVER = payload.overview || payload.summary || "";
    const KP = payload.key_patterns || payload.keyPatterns || [];
    const SNAP = payload.sentiment_snapshot || payload.sentiment || {};
    const TOPS = payload.top_subthemes || [];
    const RISKONLY = payload.risks_and_blindspots || payload.risks || [];
    const RECS = payload.recommendations || [];

    const sections = [
      {
        title: "Executive Briefing",
        type: "overview",
        content: { overview: OVER, key_patterns: Array.isArray(KP) ? KP : [] },
      },
    ];

    if (
      SNAP &&
      (SNAP.positive !== undefined ||
        SNAP.negative !== undefined ||
        SNAP.average_confidence !== undefined ||
        SNAP.overall_sentiment)
    ) {
      sections.push({
        title: "Sentiment Snapshot",
        type: "sentiment",
        content: {
          summary: "",
          counts: {
            positive: SNAP.positive ?? 0,
            negative: SNAP.negative ?? 0,
            average_confidence: SNAP.average_confidence,
          },
          overall: SNAP.overall_sentiment,
        },
      });
    }

    if (Array.isArray(TOPS) && TOPS.length) {
      sections.push({
        title: "Top Subthemes",
        type: "list",
        content: TOPS.map((x) =>
          typeof x === "string"
            ? x
            : x.subtheme
            ? `${x.subtheme} — ${x.count ?? 0}`
            : JSON.stringify(x)
        ),
      });
    }

    if (Array.isArray(RISKONLY) && RISKONLY.length) {
      sections.push({
        title: "Risks & Blindspots",
        type: "list",
        content: RISKONLY,
      });
    }

    if (Array.isArray(RECS) && RECS.length) {
      sections.push({
        title: "Actionable Recommendations",
        type: "actions",
        content: RECS,
      });
    }

    return { title: payload.dimension || payload.title || "Dimension", sections };
  }

  // subtheme
  if (kind === "subtheme") {
    const OVER = payload.overview || payload.summary || "";
    const KP = payload.key_patterns || payload.keyPatterns || [];
    const SNAP = payload.sentiment_snapshot || payload.sentiment || {};
    const CTX = payload.typical_contexts || [];
    const RISKONLY = payload.risks_and_blindspots || payload.risks || [];
    const RECS = payload.recommendations || [];
    const parents = payload.parent_dimensions || payload.parentDimensions || [];

    const sections = [
      {
        title: "Executive Briefing",
        type: "overview",
        content: { overview: OVER, key_patterns: Array.isArray(KP) ? KP : [] },
      },
    ];

    if (
      SNAP &&
      (SNAP.positive !== undefined ||
        SNAP.negative !== undefined ||
        SNAP.average_confidence !== undefined ||
        SNAP.overall_sentiment)
    ) {
      sections.push({
        title: "Sentiment Snapshot",
        type: "sentiment",
        content: {
          summary: "",
          counts: {
            positive: SNAP.positive ?? 0,
            negative: SNAP.negative ?? 0,
            average_confidence: SNAP.average_confidence,
          },
          overall: SNAP.overall_sentiment,
        },
      });
    }

    if (Array.isArray(CTX) && CTX.length) {
      sections.push({
        title: "Typical Contexts",
        type: "list",
        content: CTX,
      });
    }

    if (Array.isArray(RISKONLY) && RISKONLY.length) {
      sections.push({
        title: "Risks & Blindspots",
        type: "list",
        content: RISKONLY,
      });
    }

    if (Array.isArray(RECS) && RECS.length) {
      sections.push({
        title: "Actionable Recommendations",
        type: "actions",
        content: RECS,
      });
    }

    return {
      title: payload.subtheme || payload.title || "Subtheme",
      metaBadges: Array.isArray(parents) ? parents.map(String) : [],
      sections,
    };
  }

  // fallback
  const OVER = payload.overview || payload.summary || "";
  const KP = payload.key_patterns || payload.keyPatterns || [];
  const RECS = payload.recommendations || [];
  const sections = [];
  if (OVER || (Array.isArray(KP) && KP.length)) {
    sections.push({
      title: "Executive Briefing",
      type: "overview",
      content: { overview: OVER, key_patterns: Array.isArray(KP) ? KP : [] },
    });
  }
  if (Array.isArray(RECS) && RECS.length) {
    sections.push({
      title: "Actionable Recommendations",
      type: "actions",
      content: RECS,
    });
  }
  return { title: payload.title || "Insights", sections };
}

// ---------------------------------------------------------
// Section rendering
// ---------------------------------------------------------
function SectionView({ sec }) {
  if (sec.type === "bullets") {
    return (
      <ul className="space-y-2 text-sm text-neutral-800">
        {sec.content.map((t, i) => (
          <li key={i} className="pl-4 relative ys-fade-item" style={{ animationDelay: `${i * 30}ms` }}>
            <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
            {t}
          </li>
        ))}
      </ul>
    );
  }
  if (sec.type === "overview") {
    const { overview, key_patterns = [] } = sec.content || {};
    return (
      <div className="space-y-3 text-sm text-neutral-800">
        {overview ? <p className="ys-fade-item">{overview}</p> : null}
        {key_patterns.length ? (
          <ul className="space-y-1">
            {key_patterns.map((t, i) => (
              <li key={i} className="pl-4 relative ys-fade-item" style={{ animationDelay: `${i * 30}ms` }}>
                <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
                {t}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  if (sec.type === "sentiment") {
    const c = sec.content?.counts || {};
    const chips = [
      `Positive ${c.positive ?? 0}`,
      `Negative ${c.negative ?? 0}`,
      ...(c.average_confidence !== undefined ? [`Avg. confidence ${c.average_confidence}`] : []),
      ...(sec.content?.overall ? [`Overall ${sec.content.overall}`] : []),
    ];
    return (
      <div className="flex flex-wrap gap-2 text-xs">
        {chips.map((x, i) => (
          <span
            key={i}
            className="px-2 py-1 rounded-full bg-white border border-[#eee7db] ys-fade-item"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            {x}
          </span>
        ))}
      </div>
    );
  }
  if (sec.type === "riskopp") {
    const risks = sec.content?.risks || [];
    const opps = sec.content?.opportunities || [];
    return (
      <div className="grid md:grid-cols-2 gap-3">
        <div className="rounded-xl border border-[#eee7db] bg-white/60 p-3 ys-fade-item">
          <div className="text-sm font-medium mb-2">Risks</div>
          <ul className="space-y-2 text-sm text-neutral-800">
            {risks.map((x, i) => (
              <li key={i} className="pl-4 relative ys-fade-item" style={{ animationDelay: `${i * 30}ms` }}>
                <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
                {typeof x === "string"
                  ? x
                  : x.name
                  ? (
                    <>
                      <b>{x.name}:</b> {x.description}
                    </>
                  )
                  : JSON.stringify(x)}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-[#eee7db] bg-white/60 p-3 ys-fade-item" style={{ animationDelay: "60ms" }}>
          <div className="text-sm font-medium mb-2">Opportunities</div>
          <ul className="space-y-2 text-sm text-neutral-800">
            {opps.map((x, i) => (
              <li key={i} className="pl-4 relative ys-fade-item" style={{ animationDelay: `${i * 30}ms` }}>
                <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
                {typeof x === "string"
                  ? x
                  : x.name
                  ? (
                    <>
                      <b>{x.name}:</b> {x.description}
                    </>
                  )
                  : JSON.stringify(x)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }
  if (sec.type === "actions") {
    return (
      <div className="space-y-3">
        {sec.content.map((a, i) => {
          const text = typeof a === "string" ? a : a.recommendation || a.text || JSON.stringify(a);
          return (
            <div
              key={i}
              className="p-3 rounded-xl bg-white shadow-sm border border-[#eee7db] ys-fade-item"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div className="text-[15px] font-medium mb-1">{text}</div>
              {typeof a === "object" ? (
                <div className="text-xs text-neutral-500">
                  {a.ownership ? `Owner: ${a.ownership} · ` : ""}
                  {a.impact ? `Impact: ${a.impact}` : ""}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    );
  }
  if (sec.type === "list") {
    const arr = Array.isArray(sec.content) ? sec.content : [];
    return (
      <ul className="space-y-2 text-sm text-neutral-800">
        {arr.map((t, i) => (
          <li key={i} className="pl-4 relative ys-fade-item" style={{ animationDelay: `${i * 30}ms` }}>
            <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
            {typeof t === "string" ? t : JSON.stringify(t)}
          </li>
        ))}
      </ul>
    );
  }
  return null;
}

// ---------------------------------------------------------
// Main Component
// ---------------------------------------------------------
export default function SuggestionSummary({
  className = "",
  dimension = "",
  subthemeFile = "",
  // onBack, 
}) {
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState(null);

  const [viewKey, setViewKey] = useState(0);

  const model = useMemo(() => normalizePayload(payload), [payload]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        let data;
        if (subthemeFile) data = await getCASubthemeByFile(subthemeFile);
        else if (dimension) data = await getCADimension(dimension);
        else data = await getCAOverall();
        if (alive) setPayload(data);
      } catch (e) {
        if (alive) setPayload({ title: "Insights", section: {} });
        console.error("SuggestionSummary load error:", e);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    setViewKey(k => k + 1);
    return () => {
      alive = false;
    };
  }, [dimension, subthemeFile]);

  const isOverall = !dimension && !subthemeFile;

  return (
    <div
      className={clsx(
        "rounded-2xl border border-[#d6d0c5] shadow-sm px-6 py-5 flex flex-col",
        className
      )}
      style={{ backgroundColor: "#e0d5cadb" }}
    >
      <style>{`
        .edge-scroll {
          overflow-y: scroll;
          scrollbar-width: none; /* firefox hide */
        }
        .edge-scroll::-webkit-scrollbar { width: 0; } /* chrome hide */

        .ys-fade {
          animation: ysFade 260ms cubic-bezier(0.22,1,0.36,1);
          will-change: opacity, transform;
        }
        .ys-fade-item {
          animation: ysFadeItem 220ms cubic-bezier(0.22,1,0.36,1) both;
          will-change: opacity, transform;
        }
        @keyframes ysFade {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes ysFadeItem {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .ys-fade, .ys-fade-item { animation: none !important; }
        }
      `}</style>

      <div className="flex items-center justify-between mb-1">
        <div className="min-w-0">
          <h2 key={`title-${viewKey}`} className="text-lg font-semibold truncate ys-fade">
            {model.title || "Insights"}
          </h2>

          {Array.isArray(model.metaBadges) && model.metaBadges.length > 0 && (
            <div key={`badges-${viewKey}`} className="mt-1 flex flex-wrap gap-1.5 ys-fade">
              {model.metaBadges.map((t, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-0.5 rounded-full bg-white border border-[#eee7db] ys-fade-item"
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

      </div>

      <p key={`lead-${viewKey}`} className="text-neutral-600 text-sm mb-4 ys-fade">
        {isOverall
          ? "High-level culture insights generated by the system."
          : subthemeFile
          ? "Insights for selected subtheme."
          : `Insights for “${dimension}”.`}
      </p>

      <div
        key={`content-${viewKey}`}
        className="flex-1 pr-6 mr-[-24px] edge-scroll ys-fade"
        onMouseEnter={(e) => e.currentTarget.classList.add("show-scroll")}
        onMouseLeave={(e) => e.currentTarget.classList.remove("show-scroll")}
      >
        {loading ? (
          <div className="text-sm text-neutral-500 ys-fade-item">Loading…</div>
        ) : model.sections && model.sections.length ? (
          <div className="space-y-6">
            {model.sections.map((sec, idx) => (
              <div key={idx} className="ys-fade-item" style={{ animationDelay: `${idx * 40}ms` }}>
                <div className="text-[15px] font-semibold mb-2">{sec.title}</div>
                <SectionView sec={sec} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-neutral-500 ys-fade-item">No content.</div>
        )}
      </div>
    </div>
  );
}
