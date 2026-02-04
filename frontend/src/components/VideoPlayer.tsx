"use client";

import { forwardRef, useState, useCallback } from "react";

interface VideoPlayerProps {
  src: string;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
}

export const VideoPlayer = forwardRef<HTMLVideoElement, VideoPlayerProps>(
  function VideoPlayer({ src, onTimeUpdate, onDurationChange }, ref) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [error, setError] = useState<string | null>(null);

    const togglePlay = useCallback(() => {
      const video = typeof ref === "function" ? null : ref?.current;
      if (!video) return;

      if (video.paused) {
        video.play();
      } else {
        video.pause();
      }
    }, [ref]);

    const toggleMute = useCallback(() => {
      const video = typeof ref === "function" ? null : ref?.current;
      if (!video) return;

      video.muted = !video.muted;
      setIsMuted(video.muted);
    }, [ref]);

    const toggleFullscreen = useCallback(() => {
      const video = typeof ref === "function" ? null : ref?.current;
      if (!video) return;

      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        video.requestFullscreen();
      }
    }, [ref]);

    const handleSeek = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        const video = typeof ref === "function" ? null : ref?.current;
        if (!video) return;

        const time = parseFloat(e.target.value);
        video.currentTime = time;
        setCurrentTime(time);
      },
      [ref]
    );

    const formatTime = (seconds: number) => {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins}:${secs.toString().padStart(2, "0")}`;
    };

    return (
      <div className="flex h-full flex-col">
        {/* Video container - uses min-h-0 to allow shrinking */}
        <div className="relative min-h-0 flex-1 flex items-center justify-center bg-black">
          {error ? (
            <div className="text-center p-4">
              <p className="text-red-400 mb-2">Failed to load video</p>
              <p className="text-gray-400 text-sm">{error}</p>
              <p className="text-gray-500 text-xs mt-2">Source: {src}</p>
            </div>
          ) : (
            <video
              ref={ref}
              src={src}
              className="max-h-full max-w-full"
              onTimeUpdate={(e) => {
                const time = e.currentTarget.currentTime;
                setCurrentTime(time);
                onTimeUpdate?.(time);
              }}
              onLoadedMetadata={(e) => {
                const dur = e.currentTarget.duration;
                setDuration(dur);
                onDurationChange?.(dur);
                setError(null);
              }}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onError={(e) => {
                const video = e.currentTarget;
                const mediaError = video.error;
                let message = "Unknown error";
                if (mediaError) {
                  switch (mediaError.code) {
                    case MediaError.MEDIA_ERR_ABORTED:
                      message = "Video loading was aborted";
                      break;
                    case MediaError.MEDIA_ERR_NETWORK:
                      message = "Network error while loading video";
                      break;
                    case MediaError.MEDIA_ERR_DECODE:
                      message = "Video decoding error";
                      break;
                    case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                      message = "Video format not supported or file not found";
                      break;
                  }
                }
                setError(message);
              }}
            >
              Your browser does not support the video tag.
            </video>
          )}
        </div>

        {/* Custom controls - shrink-0 prevents controls from being cut off */}
        <div className="flex shrink-0 items-center gap-1.5 bg-gray-900 px-2 py-1.5 sm:gap-3 sm:px-4 sm:py-2">
          {/* Play/Pause button */}
          <button
            onClick={togglePlay}
            className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-full bg-white text-gray-900 hover:bg-gray-200 transition-colors"
            title={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg className="h-4 w-4 sm:h-5 sm:w-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 sm:h-5 sm:w-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Time display */}
          <span className="font-mono text-[10px] sm:text-sm text-white whitespace-nowrap">
            {formatTime(currentTime)}/{formatTime(duration)}
          </span>

          {/* Seek bar */}
          <input
            type="range"
            min={0}
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            className="flex-1 min-w-[60px] h-1.5 sm:h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-white"
          />

          {/* Volume/Mute button - hidden on very small screens */}
          <button
            onClick={toggleMute}
            className="hidden sm:flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center rounded text-white hover:bg-gray-700 transition-colors"
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? (
              <svg className="h-4 w-4 sm:h-5 sm:w-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 sm:h-5 sm:w-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
              </svg>
            )}
          </button>

          {/* Fullscreen button */}
          <button
            onClick={toggleFullscreen}
            className="flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center rounded text-white hover:bg-gray-700 transition-colors"
            title="Fullscreen"
          >
            <svg className="h-4 w-4 sm:h-5 sm:w-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
            </svg>
          </button>
        </div>
      </div>
    );
  }
);
