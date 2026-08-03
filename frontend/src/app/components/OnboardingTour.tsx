"use client";

import { useEffect, useState, useRef } from "react";

interface Step {
  target: string;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    target: "#masthead",
    title: "The Masthead & Journal Title",
    description: "Welcome to The Republic Bulletin. This masthead anchors each daily edition and the reader controls above it adjust the paper to your needs.",
  },
  {
    target: "#featured-dispatch",
    title: "Featured Lead Story",
    description: "Here lies our lead chronicle of the day. Read the full story by clicking the title or the outline button below it.",
  },
  {
    target: "#category-bar",
    title: "Archive Categories",
    description: "Filter dispatches by their category here. Choose between Technology, Opinion, Science, Sports, or Global news.",
  },
  {
    target: "#account-controls",
    title: "User Registry & Printing Portals",
    description: "Create an account or log in here. Registered journalists and editors can access their private panels to write, edit, and publish dispatches.",
  },
];

export default function OnboardingTour() {
  const [showWelcome, setShowWelcome] = useState(false);
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [popoverStyle, setPopoverStyle] = useState<React.CSSProperties>({});
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const completed = localStorage.getItem("hasCompletedOnboarding");
      if (!completed) {
        setShowWelcome(true);
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (currentStep === null) return;

    const updatePosition = () => {
      const step = STEPS[currentStep];
      const el = document.querySelector(step.target);
      if (el) {
        const rect = el.getBoundingClientRect();
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const scrollLeft = window.scrollX || document.documentElement.scrollLeft;

        // Position popover relative to the target element
        // Default: directly below the target element, centered
        let top = rect.bottom + scrollTop + 15;
        let left = rect.left + scrollLeft + (rect.width / 2) - 150; // centering 300px popover

        // Keep inside window bounds horizontally
        const windowWidth = window.innerWidth;
        if (left < 10) {
          left = 10;
        } else if (left + 310 > windowWidth) {
          left = windowWidth - 320;
        }

        // Adjust vertical position if it falls off the bottom of the page
        const windowHeight = window.innerHeight;
        if (rect.bottom + 250 > windowHeight && rect.top > 250) {
          // Position above the element
          top = rect.top + scrollTop - 230;
        }

        setPopoverStyle({
          position: "absolute",
          top: `${top}px`,
          left: `${left}px`,
          width: "300px",
          zIndex: 1000,
        });

        // Add highlight class
        el.classList.add("vintage-highlight");
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    };

    const timer = setTimeout(updatePosition, 100);

    window.addEventListener("resize", updatePosition);

    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", updatePosition);
      const step = STEPS[currentStep];
      const el = document.querySelector(step.target);
      if (el) {
        el.classList.remove("vintage-highlight");
      }
    };
  }, [currentStep]);

  const handleStart = () => {
    setShowWelcome(false);
    setCurrentStep(0);
  };

  const handleSkip = () => {
    setShowWelcome(false);
    setCurrentStep(null);
    localStorage.setItem("hasCompletedOnboarding", "true");
  };

  const handleNext = () => {
    if (currentStep === null) return;
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleSkip(); // Finish tour
    }
  };

  const handleBack = () => {
    if (currentStep === null) return;
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  if (showWelcome) {
    return (
      <div className="vintage-modal-overlay">
        <div className="vintage-modal-card">
          <h3 className="vintage-modal-title">THE REPUBLIC BULLETIN</h3>
          <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", textAlign: "center", marginBottom: "1rem", letterSpacing: "1px" }}>
            [ ESTABLISHED 2026 ]
          </h4>
          <hr className="border-double-y" style={{ border: "none", height: "4px", margin: "1rem 0" }} />
          <p style={{ fontSize: "0.95rem", lineHeight: "1.6", marginBottom: "1.5rem", textAlign: "justify" }}>
            Welcome, Gentle Reader! Would you care for a brief, guided tour of our news printing press front page to learn how to navigate the chronicles, leave responses, and access panels?
          </p>
          <div style={{ display: "flex", gap: "1rem" }}>
            <button onClick={handleStart} className="btn-press" style={{ flex: 1, padding: "0.6rem" }}>
              BEGIN TOUR
            </button>
            <button onClick={handleSkip} className="btn-press-outline" style={{ flex: 1, padding: "0.6rem" }}>
              NO, THANKS
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === null) return null;

  const step = STEPS[currentStep];

  return (
    <>
      {/* Backdrop */}
      <div 
        onClick={handleSkip} 
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          backgroundColor: "rgba(0, 0, 0, 0.25)",
          zIndex: 998,
        }} 
      />

      {/* Popover */}
      <div ref={popoverRef} style={popoverStyle} className="vintage-popover-card">
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", fontFamily: "var(--font-mono)", marginBottom: "0.5rem", color: "gray" }}>
          <span>[ GUIDE STEP {currentStep + 1} OF {STEPS.length} ]</span>
          <button onClick={handleSkip} style={{ background: "none", border: "none", textDecoration: "underline", cursor: "pointer", fontSize: "0.65rem", color: "gray" }}>
            SKIP
          </button>
        </div>
        <h4 style={{ fontFamily: "var(--font-headline)", fontSize: "1.1rem", fontWeight: "bold", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          {step.title}
        </h4>
        <p style={{ fontSize: "0.85rem", lineHeight: "1.5", marginBottom: "1rem", textAlign: "justify" }}>
          {step.description}
        </p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button 
            onClick={handleBack} 
            disabled={currentStep === 0}
            className="btn-press-outline" 
            style={{ fontSize: "0.7rem", padding: "0.25rem 0.5rem", opacity: currentStep === 0 ? 0.3 : 1 }}
          >
            ← BACK
          </button>
          <button 
            onClick={handleNext} 
            className="btn-press" 
            style={{ fontSize: "0.7rem", padding: "0.25rem 0.5rem" }}
          >
            {currentStep === STEPS.length - 1 ? "FINISH TOUR" : "NEXT →"}
          </button>
        </div>
      </div>
    </>
  );
}

