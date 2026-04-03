'use client';

import { useState, useCallback } from 'react';
import { UploadedFile } from '@/lib/types';
import { MAX_FILE_SIZE, ALLOWED_FILE_TYPES, ERROR_MESSAGES } from '@/lib/constants';
import { apiFetch } from '@/lib/api';
import {
  classifyHttpError,
  classifyThrownError,
  errorKindTitle,
  type ClassifiedError,
} from '@/lib/errors';
import { toast } from '@/hooks/use-toast';

export function useFileUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) return ERROR_MESSAGES.FILE_TOO_LARGE;
    if (!ALLOWED_FILE_TYPES.includes(file.type)) return ERROR_MESSAGES.FILE_TYPE_NOT_ALLOWED;
    return null;
  };

  const uploadFiles = useCallback(async (fileList: FileList | File[]) => {
    setIsUploading(true);
    const uploaded: UploadedFile[] = [];

    for (const file of Array.from(fileList)) {
      const err = validateFile(file);
      if (err) continue;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await apiFetch('/documents/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const text = await response.text();
          throw classifyHttpError(response.status, text);
        }

        const data = await response.json();

        uploaded.push({
          id: data.id,
          name: data.original_name,
          type: file.type,
          size: file.size,
        });
      } catch (err) {
        const classified = classifyThrownError(err);
        toast({
          variant: 'destructive',
          title: errorKindTitle(classified.kind),
          description: classified.message,
        });
      }
    }

    setFiles((prev) => [...prev, ...uploaded]);
    setIsUploading(false);
    return uploaded;
  }, []);

  return { files, uploadFiles, isUploading, error };
}