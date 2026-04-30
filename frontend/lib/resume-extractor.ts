import * as pdfjsLib from 'pdfjs-dist'

// Set up the worker
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`
}

export interface ExtractedResume {
  text: string
  skills: string[]
  jobTitles: string[]
  yearsExperience: number
  education: string[]
}

// Common skills to detect
const SKILLS_KEYWORDS = [
  'javascript',
  'typescript',
  'react',
  'node.js',
  'python',
  'java',
  'c++',
  'sql',
  'html',
  'css',
  'aws',
  'docker',
  'kubernetes',
  'git',
  'figma',
  'design',
  'ux',
  'ui',
  'product',
  'management',
  'communication',
  'leadership',
  'analysis',
  'data science',
  'machine learning',
  'ai',
  'cloud',
  'devops',
  'agile',
  'scrum',
  'rest api',
  'graphql',
  'mongodb',
  'postgresql',
  'firebase',
  'nextjs',
  'vue',
  'angular',
  'php',
  'go',
  'rust',
  'swift',
  'kotlin',
  'excel',
  'salesforce',
  'marketing',
  'sales',
  'accounting',
  'finance',
  'hr',
  'recruitment',
]

// Job titles to detect
const JOB_TITLES = [
  'software engineer',
  'developer',
  'frontend engineer',
  'backend engineer',
  'full stack engineer',
  'data scientist',
  'product manager',
  'designer',
  'ux designer',
  'ui designer',
  'devops engineer',
  'qa engineer',
  'test engineer',
  'data analyst',
  'business analyst',
  'project manager',
  'intern',
  'analyst',
  'engineer',
  'manager',
  'lead',
  'architect',
  'consultant',
]

export async function extractFromPDF(file: File): Promise<ExtractedResume> {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  
  let fullText = ''
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const textContent = await page.getTextContent()
    const text = textContent.items.map((item: any) => item.str).join(' ')
    fullText += text + ' '
  }

  const lowerText = fullText.toLowerCase()
  
  // Extract skills
  const skills = SKILLS_KEYWORDS.filter((skill) => lowerText.includes(skill))
  
  // Extract job titles
  const jobTitles = JOB_TITLES.filter((title) => lowerText.includes(title))
  
  // Extract years of experience (look for patterns like "3 years" or "3+ years")
  const yearsMatch = fullText.match(/(\d+)\+?\s+years?/i)
  const yearsExperience = yearsMatch ? parseInt(yearsMatch[1], 10) : 0
  
  // Extract education (look for common degree patterns)
  const educationKeywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
  const education: string[] = []
  educationKeywords.forEach((keyword) => {
    if (lowerText.includes(keyword)) {
      education.push(keyword)
    }
  })
  
  return {
    text: fullText,
    skills: [...new Set(skills)], // Remove duplicates
    jobTitles: [...new Set(jobTitles)],
    yearsExperience,
    education,
  }
}
