import React, { useState } from 'react';
import { Star } from 'lucide-react';

export const StarRating = ({ rating = 5, onChange, editable = true, size = 20 }) => {
  const [hoverRating, setHoverRating] = useState(0);

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => {
        const active = (hoverRating || rating) >= star;
        return (
          <button
            key={star}
            type="button"
            disabled={!editable}
            onClick={() => editable && onChange && onChange(star)}
            onMouseEnter={() => editable && setHoverRating(star)}
            onMouseLeave={() => editable && setHoverRating(0)}
            className={`transition-transform ${
              editable ? 'hover:scale-125 cursor-pointer focus:outline-none' : 'cursor-default'
            }`}
          >
            <Star
              size={size}
              className={`transition-colors ${
                active
                  ? 'fill-amber-400 text-amber-400 filter drop-shadow-[0_0_6px_rgba(251,191,36,0.5)]'
                  : 'text-zinc-600'
              }`}
            />
          </button>
        );
      })}
    </div>
  );
};

export default StarRating;
