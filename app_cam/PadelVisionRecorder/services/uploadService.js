import axios from 'axios';
const API_URL = 'https://ton-backend.com/upload';
export const uploadVideoSegments = async (uris, { onProgress } = {}) => {
  const total = uris.length;
  if (!total) return;
  for (let index = 0; index < total; index += 1) {
    const uri = uris[index];
    const formData = new FormData();
    formData.append('file', { uri, name: `match_part_${index + 1}.mp4`, type: 'video/mp4' });
    formData.append('part', `${index + 1}`);
    formData.append('totalParts', `${total}`);
    await axios.post(API_URL, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (onProgress) onProgress((index + 1) / total);
  }
};
export const uploadVideo = async (uri, options) => uploadVideoSegments([uri], options);
