import { useQuery } from '@tanstack/react-query';
import { subjectService } from '../services/subjectService';

export function useSubjects() {
  const query = useQuery({ queryKey: ['subjects'], queryFn: subjectService.getSubjects });
  return { subjects: query.data ?? [], isLoading: query.isLoading };
}
