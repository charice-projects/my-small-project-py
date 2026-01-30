const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const HtmlPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    background: './src/background/index.ts',
    content: './src/content/index.ts',
    popup: './src/popup/index.ts',
    options: './src/options/index.ts'
  },
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, 'dist'),
    clean: true
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.(png|svg|jpg|jpeg|gif)$/i,
        type: 'asset/resource'
      }
    ]
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js']
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: 'manifest.json', to: '.' },
        { from: 'assets', to: 'assets' }
      ]
    }),
    new HtmlPlugin({
      template: './src/popup/index.html',
      filename: 'popup/index.html',
      chunks: ['popup']
    }),
    new HtmlPlugin({
      template: './src/options/index.html',
      filename: 'options/index.html',
      chunks: ['options']
    })
  ]
};