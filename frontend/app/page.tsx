'use client';

import { useState, useMemo, useEffect } from 'react';
import { Header } from '@/components/header';
import { SearchBar } from '@/components/search-bar';
import { FilterSidebar } from '@/components/filter-sidebar';
import { JobCard } from '@/components/job-card';
import { ResumeUpload } from '@/components/resume-upload';
import { Card } from '@/components/ui/card';

// Mock job data
const JOBS = [
  {
    id: '1',
    title: 'Senior Frontend Engineer',
    company: 'TechFlow Inc',
    location: 'San Francisco, CA',
    type: 'Full-time',
    salary: '$150K - $200K',
    description: 'Build scalable user interfaces and drive innovation in frontend technology. Work with React, Next.js, and modern tooling.',
    rating: 4.8,
    reviews: 127,
    match: 92,
  },
  {
    id: '2',
    title: 'Product Manager Internship',
    company: 'StartupXYZ',
    location: 'Remote',
    type: 'Internship',
    salary: '$25K - $35K',
    description: 'Shape the future of our product. Work on feature prioritization, user research, and cross-functional collaboration.',
    rating: 4.6,
    reviews: 45,
    match: 85,
  },
  {
    id: '3',
    title: 'Full Stack Developer',
    company: 'Digital Innovations',
    location: 'New York, NY',
    type: 'Full-time',
    salary: '$120K - $160K',
    description: 'Develop end-to-end applications using modern JavaScript frameworks. Mentor junior developers and drive technical excellence.',
    rating: 4.7,
    reviews: 89,
    match: 88,
  },
  {
    id: '4',
    title: 'UX/UI Designer',
    company: 'Creative Studio',
    location: 'Hybrid',
    type: 'Full-time',
    salary: '$110K - $140K',
    description: 'Design beautiful and intuitive user experiences. Collaborate with engineers and product teams to deliver pixel-perfect interfaces.',
    rating: 4.9,
    reviews: 156,
    match: 79,
  },
  {
    id: '5',
    title: 'Data Science Intern',
    company: 'AI Research Labs',
    location: 'Remote',
    type: 'Internship',
    salary: '$30K - $45K',
    description: 'Work on cutting-edge machine learning projects. Analyze complex datasets and contribute to model development.',
    rating: 4.5,
    reviews: 62,
    match: 81,
  },
  {
    id: '6',
    title: 'DevOps Engineer',
    company: 'CloudTech Solutions',
    location: 'On-site',
    type: 'Full-time',
    salary: '$140K - $180K',
    description: 'Manage infrastructure, improve CI/CD pipelines, and ensure system reliability. Work with Kubernetes, Docker, and cloud platforms.',
    rating: 4.6,
    reviews: 78,
    match: 86,
  },
];

export default function Page() {
  const [jobs, setJobs] = useState<any[]>(JOBS);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    jobType: [] as string[],
    location: [] as string[],
    salaryRange: [30, 150],
    experience: [] as string[],
  });
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'match' | 'rating' | 'recent'>('match');
  const [resumeUploaded, setResumeUploaded] = useState(false);
  const [extractedSkills, setExtractedSkills] = useState<string[]>([]);
  const [showSavedOnly, setShowSavedOnly] = useState(false);

  // Call backend when search query changes
  useEffect(() => {
    if (!searchQuery) return;

    const timeoutId = setTimeout(async () => {
      try {
        const response = await fetch('http://localhost:8000/recommend/profile', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_title: searchQuery,
            skills: [searchQuery],
            desired_titles: [searchQuery]
          })
        });
        if (response.ok) {
          const data = await response.json();
          if (data.recommendations) {
            const newJobs = data.recommendations.map((rec: any) => {
              const minSal = Math.floor(Math.random() * 80) + 40;
              const expLevels = ['Entry Level', 'Mid Level', 'Senior'];
              const exp = expLevels[Math.floor(Math.random() * expLevels.length)];

              return {
                id: rec.job_id,
                title: rec.title,
                company: rec.company || 'Unknown Company',
                location: rec.location || 'On-site',
                type: rec.contract || 'Full-time',
                salary: `$${minSal}K - $${minSal + 30}K`,
                experience: exp,
                description: `Score: ${(rec.score * 100).toFixed(1)}%. Skills: ${(rec.skills || []).join(', ')}`,
                rating: 5.0,
                reviews: Math.floor(Math.random() * 50) + 10,
                match: Math.round(rec.score * 100),
                url: rec.url,
              };
            });
            setJobs(newJobs);
          }
        }
      } catch (err) {
        console.error('Search failed:', err);
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Filter and search jobs
  const filteredJobs = useMemo(() => {
    let result = jobs;
    if (showSavedOnly) {
      result = result.filter(job => savedJobs.has(job.id));
    }

    return result.filter((job) => {
      // Job type filter
      if (filters.jobType.length > 0) {
        const typeStr = (job.type || '').toLowerCase();
        const hasMatch = filters.jobType.some((t: string) => {
          const tLow = t.toLowerCase();
          if (tLow === 'full-time' && (typeStr.includes('cdi') || typeStr.includes('full'))) return true;
          if (tLow === 'contract' && (typeStr.includes('cdd') || typeStr.includes('contract'))) return true;
          if (tLow === 'part-time' && typeStr.includes('part')) return true;
          if (tLow === 'internship' && (typeStr.includes('stage') || typeStr.includes('intern'))) return true;
          return typeStr.includes(tLow);
        });
        if (!hasMatch) return false;
      }

      // Location filter
      if (filters.location.length > 0) {
        const locStr = (job.location || '').toLowerCase();
        const hasMatchingLocation = filters.location.some((loc: string) => {
          if (loc === 'Remote') return locStr.includes('remote');
          if (loc === 'Hybrid') return locStr.includes('hybrid');
          if (loc === 'On-site') return !locStr.includes('remote') && !locStr.includes('hybrid');
          return false;
        });
        if (!hasMatchingLocation) return false;
      }

      // Experience filter
      if (filters.experience && filters.experience.length > 0) {
        if (!filters.experience.includes(job.experience)) {
          return false;
        }
      }

      // Salary filter (extract minimum salary for comparison)
      const salaryMatch = job.salary?.match(/\$(\d+)K/);
      if (salaryMatch) {
        const minSalary = parseInt(salaryMatch[1]);
        if (minSalary < filters.salaryRange[0] || minSalary > filters.salaryRange[1]) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      if (sortBy === 'match') return b.match - a.match;
      if (sortBy === 'rating') return b.rating - a.rating;
      return 0; // 'recent' keeps original order
    });
  }, [jobs, filters, sortBy, showSavedOnly, savedJobs]);

  const handleSaveJob = (id: string) => {
    setSavedJobs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <Header
        showSavedOnly={showSavedOnly}
        onSavedClick={() => setShowSavedOnly(!showSavedOnly)}
        onGetStartedClick={() => {
          const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement;
          if (searchInput) searchInput.focus();
        }}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Resume Upload Section */}
        {!resumeUploaded && (
          <div className="mb-12 rounded-2xl bg-gradient-to-br from-primary/5 to-accent/5 p-8 border border-primary/10">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">Upload Your Resume</h2>
              <p className="text-muted-foreground">We&apos;ll analyze your skills and experience to personalize your recommendations</p>
            </div>
            <ResumeUpload onUploadSuccess={(data) => {
              setResumeUploaded(true);
              if (data.cv_info?.skills_found) {
                setExtractedSkills(data.cv_info.skills_found);
              }
              if (data.recommendations) {
                const newJobs = data.recommendations.map((rec: any) => {
                  const minSal = Math.floor(Math.random() * 80) + 40;
                  const expLevels = ['Entry Level', 'Mid Level', 'Senior'];
                  const exp = expLevels[Math.floor(Math.random() * expLevels.length)];

                  return {
                    id: rec.job_id,
                    title: rec.title,
                    company: rec.company || 'Unknown Company',
                    location: rec.location || 'On-site',
                    type: rec.contract || 'Full-time',
                    salary: `$${minSal}K - $${minSal + 30}K`,
                    experience: exp,
                    description: `Score: ${(rec.score * 100).toFixed(1)}%. Skills: ${(rec.skills || []).join(', ')}`,
                    rating: 5.0,
                    reviews: Math.floor(Math.random() * 100) + 5,
                    match: Math.round(rec.score * 100),
                    url: rec.url,
                  };
                });
                setJobs(newJobs);
              }
            }} />
          </div>
        )}

        {/* Search Section */}
        <div className="mb-8">
          <div className="mb-6">
            <h2 className="text-3xl font-bold text-foreground mb-2">Find Your Next Opportunity</h2>
            <p className="text-muted-foreground">
              {resumeUploaded
                ? `Explore personalized recommendations based on your resume (${extractedSkills.length} skills detected)`
                : 'Upload your resume to get personalized job and internship recommendations'}
            </p>
          </div>
          <SearchBar onSearch={setSearchQuery} />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <aside className="lg:col-span-1">
            <FilterSidebar onFiltersChange={setFilters} />
          </aside>

          {/* Job Listings */}
          <div className="lg:col-span-3">
            {/* Sort Options */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-sm text-muted-foreground">
                  Showing <span className="font-semibold text-foreground">{filteredJobs.length}</span> opportunities
                </p>
              </div>
              <div className="flex gap-2">
                {(['match', 'rating', 'recent'] as const).map((option) => (
                  <button
                    key={option}
                    onClick={() => setSortBy(option)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${sortBy === option
                        ? 'bg-primary text-white dark:text-black'
                        : 'bg-secondary text-foreground hover:bg-secondary/80'
                      }`}
                  >
                    {option === 'match' && 'Best Match'}
                    {option === 'rating' && 'Top Rated'}
                    {option === 'recent' && 'Recent'}
                  </button>
                ))}
              </div>
            </div>

            {/* Job Cards */}
            <div className="space-y-4">
              {filteredJobs.length > 0 ? (
                filteredJobs.map((job) => (
                  <JobCard
                    key={job.id}
                    {...job}
                    onSave={handleSaveJob}
                    isSaved={savedJobs.has(job.id)}
                  />
                ))
              ) : (
                <Card className="p-12 text-center border-border/60">
                  <div className="text-muted-foreground">
                    <p className="text-lg font-medium mb-2">No opportunities found</p>
                    <p className="text-sm">Try adjusting your search or filters</p>
                  </div>
                </Card>
              )}
            </div>
          </div>
        </div>

        {/* Personalization Section */}
        <div className="mt-16 pt-12 border-t border-border/40">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="border-border/60 p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-primary font-bold">📊</span>
                </div>
                <h3 className="font-semibold text-foreground">Your Profile</h3>
              </div>
              <p className="text-sm text-muted-foreground">Keep your profile updated so we can give you better recommendations</p>
            </Card>

            <Card className="border-border/60 p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-primary font-bold">⭐</span>
                </div>
                <h3 className="font-semibold text-foreground">Rate Companies</h3>
              </div>
              <p className="text-sm text-muted-foreground">Help others by sharing your experience and rating companies</p>
            </Card>

            <Card className="border-border/60 p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-primary font-bold">🎯</span>
                </div>
                <h3 className="font-semibold text-foreground">Get Alerts</h3>
              </div>
              <p className="text-sm text-muted-foreground">Create alerts for your dream jobs and never miss an opportunity</p>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
