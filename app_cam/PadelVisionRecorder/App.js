import { registerRootComponent } from 'expo';
import React, { useEffect } from 'react';
import { useKeepAwake } from 'expo-keep-awake';
import * as ScreenOrientation from 'expo-screen-orientation';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import CameraScreen from './screens/CameraScreen';
import FramingAssistScreen from './screens/FramingAssistScreen';
import UploadScreen from './screens/UploadScreen';

const Stack = createNativeStackNavigator();

function App() {
  useKeepAwake();

  useEffect(() => {
    async function lockOrientation() {
      await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT);
    }
    lockOrientation();
  }, []);

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

export default registerRootComponent(App);
