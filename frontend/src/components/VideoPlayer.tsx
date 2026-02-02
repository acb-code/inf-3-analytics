"use client";

import { forwardRef } from "react";

interface VideoPlayerProps {
  src: string;
  onTimeUpdate?: (currentTime: number) => void;
}

export const VideoPlayer = forwardRef<HTMLVideoElement, VideoPlayerProps>(
  function VideoPlayer({ src, onTimeUpdate }, ref) {
    return (
      <div className="relative w-full overflow-hidden rounded-lg bg-black">
        <video
          ref={ref}
          src={src}
          controls
          className="w-full"
          onTimeUpdate={(e) => {
            onTimeUpdate?.(e.currentTarget.currentTime);
          }}
        >
          Your browser does not support the video tag.
        </video>
      </div>
    );
  }
);
