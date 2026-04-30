'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';

interface FilterSidebarProps {
  onFiltersChange?: (filters: any) => void;
}

export function FilterSidebar({ onFiltersChange }: FilterSidebarProps) {
  const [expandedFilters, setExpandedFilters] = useState<Record<string, boolean>>({
    jobType: true,
    location: true,
    salary: true,
    experience: true,
  });

  const [filters, setFilters] = useState({
    jobType: [] as string[],
    location: [] as string[],
    salaryRange: [30, 150],
    experience: [] as string[],
  });

  const toggleFilter = (group: string) => {
    setExpandedFilters((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  const handleCheckboxChange = (group: string, value: string) => {
    const items = filters[group as keyof typeof filters] as string[];
    const newItems = items.includes(value)
      ? items.filter((item) => item !== value)
      : [...items, value];
    const updated = { ...filters, [group]: newItems };
    
    setFilters(updated);
    onFiltersChange?.(updated);
  };

  const handleSalaryChange = (value: number[]) => {
    const updated = { ...filters, salaryRange: value };
    setFilters(updated);
    onFiltersChange?.(updated);
  };

  return (
    <div className="space-y-4">
      <Card className="border-border/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Job Type */}
          <div>
            <button
              onClick={() => toggleFilter('jobType')}
              className="flex items-center justify-between w-full mb-3 hover:text-primary transition-colors"
            >
              <h4 className="font-semibold text-sm">Job Type</h4>
              <ChevronDown
                size={18}
                className={`transition-transform ${
                  expandedFilters.jobType ? 'rotate-180' : ''
                }`}
              />
            </button>
            {expandedFilters.jobType && (
              <div className="space-y-2 pl-1">
                {['Full-time', 'Part-time', 'Internship', 'Contract'].map((type) => (
                  <div key={type} className="flex items-center gap-2">
                    <Checkbox
                      id={`type-${type}`}
                      checked={filters.jobType.includes(type)}
                      onCheckedChange={() => handleCheckboxChange('jobType', type)}
                      className="border-border/60"
                    />
                    <Label htmlFor={`type-${type}`} className="text-sm cursor-pointer font-normal">
                      {type}
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Location */}
          <div>
            <button
              onClick={() => toggleFilter('location')}
              className="flex items-center justify-between w-full mb-3 hover:text-primary transition-colors"
            >
              <h4 className="font-semibold text-sm">Location</h4>
              <ChevronDown
                size={18}
                className={`transition-transform ${
                  expandedFilters.location ? 'rotate-180' : ''
                }`}
              />
            </button>
            {expandedFilters.location && (
              <div className="space-y-2 pl-1">
                {['Remote', 'Hybrid', 'On-site'].map((loc) => (
                  <div key={loc} className="flex items-center gap-2">
                    <Checkbox
                      id={`loc-${loc}`}
                      checked={filters.location.includes(loc)}
                      onCheckedChange={() => handleCheckboxChange('location', loc)}
                      className="border-border/60"
                    />
                    <Label htmlFor={`loc-${loc}`} className="text-sm cursor-pointer font-normal">
                      {loc}
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Salary Range */}
          <div>
            <button
              onClick={() => toggleFilter('salary')}
              className="flex items-center justify-between w-full mb-3 hover:text-primary transition-colors"
            >
              <h4 className="font-semibold text-sm">Salary Range (K)</h4>
              <ChevronDown
                size={18}
                className={`transition-transform ${
                  expandedFilters.salary ? 'rotate-180' : ''
                }`}
              />
            </button>
            {expandedFilters.salary && (
              <div className="space-y-3 pl-1">
                <Slider
                  defaultValue={filters.salaryRange}
                  min={20}
                  max={200}
                  step={5}
                  onValueChange={handleSalaryChange}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>${filters.salaryRange[0]}K</span>
                  <span>${filters.salaryRange[1]}K</span>
                </div>
              </div>
            )}
          </div>

          {/* Experience Level */}
          <div>
            <button
              onClick={() => toggleFilter('experience')}
              className="flex items-center justify-between w-full mb-3 hover:text-primary transition-colors"
            >
              <h4 className="font-semibold text-sm">Experience</h4>
              <ChevronDown
                size={18}
                className={`transition-transform ${
                  expandedFilters.experience ? 'rotate-180' : ''
                }`}
              />
            </button>
            {expandedFilters.experience && (
              <div className="space-y-2 pl-1">
                {['Entry Level', 'Mid Level', 'Senior'].map((exp) => (
                  <div key={exp} className="flex items-center gap-2">
                    <Checkbox
                      id={`exp-${exp}`}
                      checked={filters.experience.includes(exp)}
                      onCheckedChange={() => handleCheckboxChange('experience', exp)}
                      className="border-border/60"
                    />
                    <Label htmlFor={`exp-${exp}`} className="text-sm cursor-pointer font-normal">
                      {exp}
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
