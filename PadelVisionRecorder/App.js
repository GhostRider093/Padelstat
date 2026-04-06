import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import CameraScreen from './screens/CameraScreen';
import FramingAssistScreen from './screens/FramingAssistScreen';
import UploadScreen from './screens/UploadScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: true }}>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="CameraScreen" component={CameraScreen} options={{ title: 'Enregistrement' }} />
        <Stack.Screen name="FramingAssistScreen" component={FramingAssistScreen} options={{ title: 'Assistant de cadrage' }} />
        <Stack.Screen name="UploadScreen" component={UploadScreen} options={{ title: 'Upload' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
