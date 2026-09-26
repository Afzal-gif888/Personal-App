import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { studyPlanService } from '../services/studyPlanService';
import type { StudySession } from '../types';
import { toast } from '../stores/notificationStore';

export function useStudyPlan() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['studySessions'],
    queryFn: () => studyPlanService.getStudySessions(),
  });

  const createMutation = useMutation({
    mutationFn: (data: Omit<StudySession, 'id'>) => studyPlanService.createSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      toast.success('Study Session Added');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<StudySession> }) => studyPlanService.updateSession(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      toast.success('Study Session Updated');
    },
  });

  const toggleCompleteMutation = useMutation({
    mutationFn: (id: string) => studyPlanService.toggleSessionComplete(id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      if (updated.status === 'completed') {
        toast.success('Session Finished', `Completed: ${updated.topic}`);
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => studyPlanService.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      toast.info('Session Removed');
    },
  });

  const generateAIMutation = useMutation({
    mutationFn: ({ subject, hours }: { subject: string; hours: number }) => studyPlanService.generateAIStudyPlan(subject, hours),
    onSuccess: (newSessions) => {
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      toast.success('AI Study Plan Created', `Generated ${newSessions.length} sessions for your schedule.`);
    },
    onError: () => toast.error('Failed to generate AI study plan'),
  });

  return {
    sessions: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    createSession: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    updateSession: updateMutation.mutateAsync,
    toggleComplete: toggleCompleteMutation.mutateAsync,
    deleteSession: deleteMutation.mutateAsync,
    generateAIPlan: generateAIMutation.mutateAsync,
    isGeneratingAI: generateAIMutation.isPending,
  };
}
