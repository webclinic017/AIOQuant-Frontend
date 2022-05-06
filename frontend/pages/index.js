import React, { useState, useCallback, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

import Head from 'next/head';
import Image from 'next/image';
import styles from '../styles/Home.module.css';
const Home = () => {
  //Public API that will echo messages sent to it back to the client
  const socketUrl = 'ws://localhost:8080';
  const [messageHistory, setMessageHistory] = useState([]);
  const { sendMessage, lastMessage, readyState } = useWebSocket(socketUrl);
  useEffect(() => {
    console.log('I received the LAST Message:::');
    if (lastMessage) {
      console.log(lastMessage.data);
    }


    if (lastMessage !== null) {
      setMessageHistory((prev) => prev.concat(lastMessage));
    }
  }, [lastMessage, setMessageHistory]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  return (
    <div className={styles.container}>
      <Head>
        <title>Create Next App</title>
        <meta name="description" content="Generated by create next app" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className={styles.main}>
        <div>
          <p>Hello World!</p>
          <span>The WebSocket is currently {connectionStatus}</span>
          {lastMessage && <p>{lastMessage.data}</p>}
        </div>
      </main>
    </div>
  );
};

export default Home;
