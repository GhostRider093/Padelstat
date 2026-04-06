import * as FileSystem from 'expo-file-system';

export async function saveRecording(tempUri) {
  const fileUri = FileSystem.documentDirectory + `match_${Date.now()}.mp4`;
  await FileSystem.moveAsync({ from: tempUri, to: fileUri });
  return fileUri;
}
