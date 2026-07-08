import api from '../../../../api/client';

export const importApi = {
  preview: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/imports/mt5/preview', formData);
  },

  confirm: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/imports/mt5/confirm', formData);
  },
};
