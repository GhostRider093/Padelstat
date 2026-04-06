import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { uploadVideoSegments } from '../services/uploadService';
export default function UploadScreen({ route }) {
  const { videoUri, segments } = route.params || {};
  const files = useMemo(() => {
    if (segments && segments.length) return segments;
    return videoUri ? [videoUri] : [];
  }, [videoUri, segments]);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const onUpload = async () => {
    if (!files.length || uploading) return;
    try {
      setUploading(true);
      setProgress(0);
      await uploadVideoSegments(files, { onProgress: setProgress });
      alert('Upload terminé');
    } catch (e) {
      alert('Upload échoué');
    } finally {
      setUploading(false);
    }
  };
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Upload du match</Text>
      {files.length ? (
        <View style={styles.listBox}>
          {files.map((file, idx) => (
            <Text key={file} style={styles.info}>
              Segment {idx + 1} : {file}
            </Text>
          ))}
        </View>
      ) : (
        <Text style={styles.info}>Aucun fichier détecté</Text>
      )}
      {uploading && (
        <Text style={styles.progress}>Progression : {(progress * 100).toFixed(0)}%</Text>
      )}
      <TouchableOpacity style={[styles.btn, uploading && styles.btnDisabled]} onPress={onUpload} disabled={uploading || !files.length}>
        <Text style={styles.btnText}>{uploading ? 'Upload en cours…' : 'Uploader'}</Text>
      </TouchableOpacity>
    </View>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 },
  title: { color: '#fff', fontSize: 22, fontWeight: 'bold', marginBottom: 24 },
  info: { color: '#ccc', marginBottom: 8 },
  listBox: { width: '100%', marginBottom: 16 },
  btn: { backgroundColor: '#333', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, marginVertical: 8 },
  btnDisabled: { backgroundColor: '#555' },
  btnText: { color: '#fff', fontWeight: 'bold' },
  progress: { color: '#fbbf24', marginBottom: 12 },
});
