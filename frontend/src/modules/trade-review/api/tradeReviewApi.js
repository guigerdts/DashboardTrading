import { api } from '../../../shared/lib/api';

export const tradeReviewApi = {
  getDetail: (id, { signal } = {}) =>
    api.get(`/trades/${id}`, { signal }),

  getReview: (id, { signal } = {}) =>
    api.get(`/trades/${id}/review`, { signal }),

  saveReview: (id, data) =>
    api.put(`/trades/${id}/review`, data),
};
