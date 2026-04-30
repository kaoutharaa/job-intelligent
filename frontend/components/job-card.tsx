'use client';

import { useState } from 'react';
import { Heart, MapPin, Briefcase, Clock, Star, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface JobCardProps {
  id: string;
  title: string;
  company: string;
  location: string;
  type: string;
  salary?: string;
  description: string;
  rating: number;
  reviews: number;
  match: number;
  url?: string;
  onSave?: (id: string) => void;
  isSaved?: boolean;
}

export function JobCard({
  id,
  title,
  company,
  location,
  type,
  salary,
  description,
  rating,
  reviews,
  match,
  url,
  onSave,
  isSaved = false,
}: JobCardProps) {
  const [saved, setSaved] = useState(isSaved);

  const handleSave = () => {
    setSaved(!saved);
    onSave?.(id);
  };

  return (
    <Card className="group hover:shadow-lg transition-all duration-300 border-border/60 hover:border-primary/30">
      <CardContent className="p-6">
        {/* Header with save button */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-foreground mb-1">
              {url ? (
                <a href={url} target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors inline-flex items-center gap-2">
                  {title}
                  <ExternalLink size={16} className="text-muted-foreground" />
                </a>
              ) : (
                title
              )}
            </h3>
            <p className="text-sm text-muted-foreground">{company}</p>
          </div>
          <button
            onClick={handleSave}
            className="p-2 rounded-full hover:bg-secondary transition-colors ml-2 flex-shrink-0"
            aria-label={saved ? 'Remove from saved' : 'Save job'}
          >
            <Heart
              size={20}
              className={saved ? 'fill-primary text-primary' : 'text-muted-foreground'}
            />
          </button>
        </div>

        {/* Job details */}
        <div className="flex flex-wrap gap-3 mb-4 text-sm">
          <div className="flex items-center gap-1 text-muted-foreground">
            <MapPin size={16} className="text-primary/60" />
            <span>{location}</span>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <Briefcase size={16} className="text-primary/60" />
            <span>{type}</span>
          </div>
          {salary && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <span className="font-medium text-foreground">{salary}</span>
            </div>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-2">
          {description}
        </p>

        {/* Rating and match percentage */}
        <div className="flex items-center justify-between pt-4 border-t border-border/40">
          <div className="flex items-center gap-3">
            {/* Rating */}
            <div className="flex items-center gap-1">
              <div className="flex items-center gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    size={14}
                    className={
                      i < Math.floor(rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-border'
                    }
                  />
                ))}
              </div>
              <span className="text-xs text-muted-foreground ml-1">
                ({reviews} {reviews === 1 ? 'review' : 'reviews'})
              </span>
            </div>
          </div>

          {/* Match percentage */}
          <div className="flex items-center gap-2">
            <div className="text-right">
              <div className="text-sm font-semibold text-primary">{match}%</div>
              <span className="text-xs text-muted-foreground">match</span>
            </div>
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-bold text-primary">{match}%</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
