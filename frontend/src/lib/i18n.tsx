"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type Lang = "en" | "fr";

const translations = {
  en: {
    // Home / Runs page
    "home.appName": "inf3 analytics",
    "home.tagline": "Infrastructure Inspection Video Analytics",
    "home.description":
      "Automates video analysis for infrastructure inspections — extracting transcripts, detecting events, sampling frames, and running AI-powered visual analysis to identify defects, equipment, and safety conditions.",
    "home.capabilities": "Transcription · Event Detection · Frame Analytics · Site Analytics",
    "home.uploadVideo": "Upload Video",
    "home.selectRun": "Select a run to view video and events",
    "home.noRuns": "No runs found. Upload a video to get started.",
    "home.errorLoading": "Error loading runs",

    // Upload page
    "upload.back": "← Back to Runs",
    "upload.title": "Infrastructure Inspection Analytics",
    "upload.description":
      "inf3-analytics automates video analysis for infrastructure inspections — extracting transcripts, detecting inspection events, sampling key frames, and running AI-powered visual analysis to identify defects, equipment, and safety conditions. Turn hours of manual video review into structured, searchable inspection data.",
    "upload.haveALongVideo": "Have a long video?",
    "upload.decomposeSuggestion":
      "Split it into smaller segments first for better reliability and parallel processing.",
    "upload.decomposeLink": "Go to Video Decomposition →",
    "upload.dragDrop": "Drag and drop a video file here, or",
    "upload.browse": "browse",
    "upload.remove": "Remove",
    "upload.uploading": "Uploading...",
    "upload.uploadButton": "Upload Video",
    "upload.longVideoTitle": "This video is {duration} long",
    "upload.longVideoBody":
      "Long videos may experience timeouts or failures during processing. Consider splitting it into smaller segments first.",
    "upload.decompose": "Decompose Video",
    "upload.continueAnyway": "Continue anyway",
    "upload.language": "Language",
    "upload.languageHint": "Transcription, events, and analytics will be in English",
    "upload.languageHint.fr": "Transcription, événements et analyses seront en français",
    "upload.longVideoNote": "This is a long video ({duration}). Processing may take a while.",

    // Run detail page
    "detail.runs": "Runs",
    "detail.viewSiteAnalytics": "View Site Analytics",
    "detail.showAnalytics": "Show Analytics",
    "detail.hideAnalytics": "Hide Analytics",
    "detail.whatsAvailable": "What's Available",
    "detail.pipeline": "Event Pipeline",
    "detail.siteAnalytics": "Site Analytics",
    "detail.language": "Language:",
    "detail.runAll": "Run All Steps",
    "detail.cancelPipeline": "Cancel Pipeline",
    "detail.runSiteAnalytics": "Run Site Analytics",
    "detail.vlmEngine": "VLM engine for frame analysis",
    "detail.detectionEngine": "Detection engine",
    "detail.events": "Events",
    "detail.errorLoading": "Error loading run",
    "detail.notFound": "Run not found",
    "detail.backToRuns": "Back to runs",

    // Step labels
    "step.transcribe": "Transcribe",
    "step.extract_events": "Extract Events",
    "step.extract_frames": "Extract Frames",
    "step.frame_analytics": "Analyze Frames",
    "step.site_analytics": "Site Analytics",

    // Step tooltips
    "tooltip.transcribe": "Extract audio and transcribe speech to text",
    "tooltip.extract_events": "Identify inspection events from transcript",
    "tooltip.extract_frames": "Sample video frames for each event",
    "tooltip.frame_analytics": "Run VLM analysis on extracted frames",
    "tooltip.site_analytics": "Detect equipment, personnel, and PPE across all frames",

    // Capabilities
    "cap.transcription.name": "Transcription",
    "cap.transcription.desc": "Speech-to-text from video audio with word-level timestamps",
    "cap.events.name": "Event Detection",
    "cap.events.desc":
      "Rules-based and LLM-powered identification of inspection events from transcript",
    "cap.frames.name": "Frame Extraction",
    "cap.frames.desc":
      "Automatic sampling of video frames at event timestamps (before, during, after each event)",
    "cap.frameAnalytics.name": "Frame Analytics",
    "cap.frameAnalytics.desc":
      "VLM analysis of extracted frames: defect detection, equipment/personnel identification, severity assessment, and structured Q&A",
    "cap.siteAnalytics.name": "Site Analytics",
    "cap.siteAnalytics.desc":
      "Whole-video detection of equipment, personnel, and PPE across sampled frames using YOLO or VLM engines",

    // Decompose page
    "decompose.back": "← Back to Runs",
    "decompose.title": "Video Decomposition",
    "decompose.description": "Split large videos into smaller segments for efficient processing",
    "decompose.step.upload": "Upload",
    "decompose.step.analyze": "Analyze",
    "decompose.step.review": "Review",
    "decompose.step.execute": "Execute",
    "decompose.step.complete": "Complete",
    "decompose.selectVideo": "Step 1: Select Video",
    "decompose.targetDuration": "Target segment duration:",
    "decompose.uploading": "Uploading...",
    "decompose.uploadAnalyze": "Upload & Analyze",
    "decompose.analyzing": "Analyzing video for optimal split points...",
    "decompose.analyzingNote": "This may take a few seconds for long videos",
    "decompose.reviewSplits": "Step 2: Review Split Points",
    "decompose.executing": "Step 3: Decomposing Video",
    "decompose.complete": "Decomposition Complete",
    "decompose.createdSegments": "Created {count} segments",
    "decompose.withChildRuns": "with {count} child runs",
    "decompose.cancel": "Cancel",
    "decompose.startDecomposition": "Start Decomposition",
    "decompose.goToRunsList": "Go to Runs List",
    "decompose.viewFirstSegment": "View First Segment",
    "decompose.createChildRuns":
      "Create separate runs for each segment (recommended)",
    "decompose.dragDrop": "Drag and drop a video file here, or",
    "decompose.browse": "browse",
    "decompose.remove": "Remove",
    "decompose.timeline": "Timeline",
    "decompose.splitPoints": "Split Points",
    "decompose.options": "Options",
    "decompose.estimated": "Estimated: {count} segments, avg {avg} each, ~{size} MB total",

    // RunCard
    "status.created": "created",
    "status.running": "running",
    "status.completed": "completed",
    "status.failed": "failed",
    "common.delete": "Delete",
    "common.deleting": "Deleting...",
    "common.forceDeleteConfirm": "This run appears to be still running. Force delete anyway? This will not stop the pipeline if it is active.",

    // Events
    "events.addManualEvent": "Add Manual Event",
    "events.noEvents": "No events found",
    "events.extractFrames": "Extract Frames",

    // Frame viewer
    "viewer.eventSummary": "Event Summary",
    "viewer.frameAnalysis": "Frame Analysis",
    "viewer.sceneSummary": "Scene Summary",
    "viewer.qa": "Q&A",
    "viewer.noAnalysis": "No analysis available for this frame",
    "viewer.frameOf": "Frame",
    "viewer.of": "of",
    "viewer.fit": "Fit",
    "viewer.model": "Model",
    "viewer.provider": "Provider",
    "viewer.close": "Close (Esc)",
    "viewer.previous": "Previous (Left Arrow)",
    "viewer.next": "Next (Right Arrow)",
    "viewer.fitToViewport": "Fit image to viewport (F)",
    "viewer.resetZoom": "Reset to 100% (0)",
    "viewer.zoomIn": "Zoom in (+)",
    "viewer.zoomOut": "Zoom out (-)",
    "viewer.detections": "Detections",
    "viewer.all": "All",
    "viewer.none": "None",
  },

  fr: {
    // Home / Runs page
    "home.appName": "inf3 analytics",
    "home.tagline": "Analyse vidéo d'inspection d'infrastructure",
    "home.description":
      "Automatise l'analyse vidéo des inspections d'infrastructure — extraction de transcriptions, détection d'événements, échantillonnage de cadres et analyse visuelle par IA pour identifier les défauts, équipements et conditions de sécurité.",
    "home.capabilities":
      "Transcription · Détection d'événements · Analyse de cadres · Analyse de site",
    "home.uploadVideo": "Téléverser une vidéo",
    "home.selectRun": "Sélectionnez une inspection pour voir la vidéo et les événements",
    "home.noRuns": "Aucune inspection trouvée. Téléversez une vidéo pour commencer.",
    "home.errorLoading": "Erreur lors du chargement des inspections",

    // Upload page
    "upload.back": "← Retour aux inspections",
    "upload.title": "Analyse d'inspection d'infrastructure",
    "upload.description":
      "inf3-analytics automatise l'analyse vidéo des inspections d'infrastructure — extraction de transcriptions, détection d'événements, échantillonnage de cadres clés et analyse visuelle par IA. Transformez des heures de révision manuelle en données d'inspection structurées et consultables.",
    "upload.haveALongVideo": "Vous avez une longue vidéo?",
    "upload.decomposeSuggestion":
      "Divisez-la en segments plus courts pour une meilleure fiabilité et un traitement parallèle.",
    "upload.decomposeLink": "Aller à la décomposition vidéo →",
    "upload.dragDrop": "Glissez-déposez une vidéo ici, ou",
    "upload.browse": "parcourir",
    "upload.remove": "Supprimer",
    "upload.uploading": "Téléversement...",
    "upload.uploadButton": "Téléverser la vidéo",
    "upload.longVideoTitle": "Cette vidéo dure {duration}",
    "upload.longVideoBody":
      "Les longues vidéos peuvent entraîner des délais d'expiration ou des échecs lors du traitement. Envisagez de la diviser en segments plus petits.",
    "upload.decompose": "Décomposer la vidéo",
    "upload.continueAnyway": "Continuer quand même",
    "upload.language": "Langue",
    "upload.languageHint": "La transcription, les événements et les analyses seront en anglais",
    "upload.languageHint.fr":
      "La transcription, les événements et les analyses seront en français",
    "upload.longVideoNote":
      "C'est une longue vidéo ({duration}). Le traitement peut prendre du temps.",

    // Run detail page
    "detail.runs": "Inspections",
    "detail.viewSiteAnalytics": "Voir l'analyse de site",
    "detail.showAnalytics": "Afficher les analyses",
    "detail.hideAnalytics": "Masquer les analyses",
    "detail.whatsAvailable": "Fonctionnalités disponibles",
    "detail.pipeline": "Pipeline d'événements",
    "detail.siteAnalytics": "Analyse de site",
    "detail.language": "Langue :",
    "detail.runAll": "Tout exécuter",
    "detail.cancelPipeline": "Annuler le pipeline",
    "detail.runSiteAnalytics": "Lancer l'analyse de site",
    "detail.vlmEngine": "Moteur VLM pour l'analyse des cadres",
    "detail.detectionEngine": "Moteur de détection",
    "detail.events": "Événements",
    "detail.errorLoading": "Erreur lors du chargement de l'inspection",
    "detail.notFound": "Inspection introuvable",
    "detail.backToRuns": "Retour aux inspections",

    // Step labels
    "step.transcribe": "Transcrire",
    "step.extract_events": "Extraire les événements",
    "step.extract_frames": "Extraire les cadres",
    "step.frame_analytics": "Analyser les cadres",
    "step.site_analytics": "Analyse de site",

    // Step tooltips
    "tooltip.transcribe": "Extraire l'audio et transcrire la parole en texte",
    "tooltip.extract_events": "Identifier les événements d'inspection depuis la transcription",
    "tooltip.extract_frames": "Échantillonner les cadres vidéo pour chaque événement",
    "tooltip.frame_analytics": "Exécuter l'analyse VLM sur les cadres extraits",
    "tooltip.site_analytics": "Détecter équipements, personnel et EPI sur tous les cadres",

    // Capabilities
    "cap.transcription.name": "Transcription",
    "cap.transcription.desc":
      "Discours-texte depuis l'audio vidéo avec horodatages au niveau des mots",
    "cap.events.name": "Détection d'événements",
    "cap.events.desc":
      "Identification des événements d'inspection par règles et LLM depuis la transcription",
    "cap.frames.name": "Extraction de cadres",
    "cap.frames.desc":
      "Échantillonnage automatique des cadres vidéo aux horodatages des événements (avant, pendant, après)",
    "cap.frameAnalytics.name": "Analyse de cadres",
    "cap.frameAnalytics.desc":
      "Analyse VLM des cadres : détection de défauts, identification équipements/personnel, évaluation de gravité et Q&R structuré",
    "cap.siteAnalytics.name": "Analyse de site",
    "cap.siteAnalytics.desc":
      "Détection globale d'équipements, personnel et EPI sur les cadres échantillonnés via YOLO ou moteurs VLM",

    // Decompose page
    "decompose.back": "← Retour aux inspections",
    "decompose.title": "Décomposition vidéo",
    "decompose.description":
      "Divisez les longues vidéos en segments plus petits pour un traitement efficace",
    "decompose.step.upload": "Téléverser",
    "decompose.step.analyze": "Analyser",
    "decompose.step.review": "Réviser",
    "decompose.step.execute": "Exécuter",
    "decompose.step.complete": "Terminé",
    "decompose.selectVideo": "Étape 1 : Sélectionner la vidéo",
    "decompose.targetDuration": "Durée cible des segments :",
    "decompose.uploading": "Téléversement...",
    "decompose.uploadAnalyze": "Téléverser et analyser",
    "decompose.analyzing": "Analyse de la vidéo pour les points de division optimaux...",
    "decompose.analyzingNote": "Cela peut prendre quelques secondes pour les longues vidéos",
    "decompose.reviewSplits": "Étape 2 : Réviser les points de division",
    "decompose.executing": "Étape 3 : Décomposition en cours",
    "decompose.complete": "Décomposition terminée",
    "decompose.createdSegments": "{count} segments créés",
    "decompose.withChildRuns": "avec {count} inspections enfants",
    "decompose.cancel": "Annuler",
    "decompose.startDecomposition": "Lancer la décomposition",
    "decompose.goToRunsList": "Voir la liste des inspections",
    "decompose.viewFirstSegment": "Voir le premier segment",
    "decompose.createChildRuns":
      "Créer des inspections séparées pour chaque segment (recommandé)",
    "decompose.dragDrop": "Glissez-déposez une vidéo ici, ou",
    "decompose.browse": "parcourir",
    "decompose.remove": "Supprimer",
    "decompose.timeline": "Chronologie",
    "decompose.splitPoints": "Points de division",
    "decompose.options": "Options",
    "decompose.estimated":
      "Estimé : {count} segments, moyenne {avg} chacun, ~{size} Mo au total",

    // RunCard
    "status.created": "créé",
    "status.running": "en cours",
    "status.completed": "terminé",
    "status.failed": "échoué",
    "common.delete": "Supprimer",
    "common.deleting": "Suppression...",
    "common.forceDeleteConfirm": "Cette inspection semble encore en cours. Forcer la suppression ? Cela n'arrêtera pas le pipeline s'il est actif.",

    // Events
    "events.addManualEvent": "Ajouter un événement manuel",
    "events.noEvents": "Aucun événement trouvé",
    "events.extractFrames": "Extraire les cadres",

    // Frame viewer
    "viewer.eventSummary": "Résumé de l'événement",
    "viewer.frameAnalysis": "Analyse du cadre",
    "viewer.sceneSummary": "Résumé de la scène",
    "viewer.qa": "Q&R",
    "viewer.noAnalysis": "Aucune analyse disponible pour ce cadre",
    "viewer.frameOf": "Cadre",
    "viewer.of": "de",
    "viewer.fit": "Ajuster",
    "viewer.model": "Modèle",
    "viewer.provider": "Fournisseur",
    "viewer.close": "Fermer (Échap)",
    "viewer.previous": "Précédent (Flèche gauche)",
    "viewer.next": "Suivant (Flèche droite)",
    "viewer.fitToViewport": "Ajuster l'image à la fenêtre (F)",
    "viewer.resetZoom": "Réinitialiser à 100% (0)",
    "viewer.zoomIn": "Zoom avant (+)",
    "viewer.zoomOut": "Zoom arrière (-)",
    "viewer.detections": "Détections",
    "viewer.all": "Tout",
    "viewer.none": "Aucun",
  },
} as const;

type TranslationKey = keyof typeof translations.en;

interface LanguageContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const stored = localStorage.getItem("inf3-lang");
    if (stored === "en" || stored === "fr") {
      setLangState(stored);
    }
  }, []);

  const setLang = (newLang: Lang) => {
    setLangState(newLang);
    localStorage.setItem("inf3-lang", newLang);
  };

  const t = (key: TranslationKey): string => {
    return translations[lang][key] ?? translations.en[key] ?? key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
