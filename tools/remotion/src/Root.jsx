import React from 'react';
import { Composition } from 'remotion';
import { Fight } from './Fight';
export const Root = () => (
  <Composition id="GokuFight" component={Fight} durationInFrames={390} fps={30} width={1080} height={1920} />
);
