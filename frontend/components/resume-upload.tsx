'use client'

import { useState } from 'react'
import { Upload, FileText, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'

interface ResumeUploadProps {
  onUploadSuccess?: (data: any) => void
}

export function ResumeUpload({ onUploadSuccess }: ResumeUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleFile = async (file: File) => {
    setError(null)
    setSuccess(false)

    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('File size must be less than 5MB')
      return
    }

    setIsLoading(true)
    setFileName(file.name)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/recommend/cv', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()

      setSuccess(true)
      if (onUploadSuccess) {
        onUploadSuccess(data)
      }

      // Reset form after 2 seconds
      setTimeout(() => {
        setFileName(null)
        setSuccess(false)
      }, 2000)
    } catch (err) {
      console.error('Resume upload error:', err)
      setError('Failed to process resume. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFile(files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-border bg-muted/30'
        } ${isLoading ? 'opacity-50' : ''}`}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileInput}
          disabled={isLoading}
          className="absolute inset-0 cursor-pointer opacity-0"
        />

        <div className="flex flex-col items-center gap-3">
          {isLoading ? (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="text-sm font-medium text-foreground">Processing your resume...</p>
            </>
          ) : success ? (
            <>
              <CheckCircle2 className="h-12 w-12 text-green-500" />
              <p className="text-sm font-medium text-green-600">Resume uploaded successfully!</p>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-primary/60" />
              <p className="text-base font-semibold text-foreground">Upload Your Resume</p>
              <p className="text-sm text-muted-foreground">
                Drag and drop your PDF here or click to browse
              </p>
            </>
          )}
        </div>

        {fileName && !isLoading && !success && (
          <p className="mt-3 flex items-center justify-center gap-2 text-sm text-foreground">
            <FileText className="h-4 w-4" />
            {fileName}
          </p>
        )}
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-destructive">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <p className="mt-2 text-xs text-muted-foreground">
        Supported format: PDF (max 5MB). We extract your skills, experience, and education to personalize your recommendations.
      </p>
    </div>
  )
}
