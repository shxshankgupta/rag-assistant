'use client';

import { useState, useCallback } from 'react';
import { UploadedFile } from '@/lib/types';
import { MAX_FILE_SIZE, ALLOWED_FILE_TYPES, ERROR_MESSAGES } from '@/lib/constants';
import { apiFetch } from '@/lib/api';
import {
  classifyHttpError,
  classifyThrownError,
  errorKindTitle,
} from '@/lib/errors';
import { toast } from '@/hooks/use-toast';

export function useFileUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File): string | null => {
    const filename = file.name.toLowerCase();
    const isPdf =
      ALLOWED_FILE_TYPES.includes(file.type) ||
      (!file.type && filename.endsWith('.pdf')) ||
      filename.endsWith('.pdf');

    if (file.size > MAX_FILE_SIZE) return ERROR_MESSAGES.FILE_TOO_LARGE;
    if (!isPdf) return ERROR_MESSAGES.FILE_TYPE_NOT_ALLOWED;
    return null;
  };

  const uploadFiles = useCallback(async (fileList: FileList | File[]) => {
    setIsUploading(true);
    setError(null);
    const uploaded: UploadedFile[] = [];

    try {
      for (const file of Array.from(fileList)) {
        const err = validateFile(file);
        if (err) {
          setError(err);
          toast({
            variant: 'destructive',
            title: 'Invalid file',
            description: err,
          });
          continue;
        }

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
            type: file.type || 'application/pdf',
            size: file.size,
          });
        } catch (err) {
          const classified = classifyThrownError(err);
          setError(classified.message);
          toast({
            variant: 'destructive',
            title: errorKindTitle(classified.kind),
            description: classified.message,
          });
        }
      }
    } finally {
      setIsUploading(false);
    }

    setFiles((prev) => [...prev, ...uploaded]);
    return uploaded;
  }, []);

  return { files, uploadFiles, isUploading, error };
}
