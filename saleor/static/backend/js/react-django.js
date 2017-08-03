import React, { PropTypes } from 'react';
import ReactDOM from 'react-dom';
import Relay from 'react-relay';
import $ from 'jquery';

const WritePage = document.getElementById('write-message');

class App extends React.Component {

  render() {
    return <div>
                <h2>Hello world</h2>
           </div>
  }
}
ReactDOM.render(<App />, document.getElementById('write-message'));
