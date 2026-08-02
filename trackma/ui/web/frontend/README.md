# Trackma web interface

React and TypeScript frontend rendered by Trackma's Qt WebEngine desktop shell.

```sh
npm install
npm run dev
```

Launch the Python shell against the development server with:

```sh
trackma --dev-url http://127.0.0.1:5173
```

`npm run build` writes the packaged interface to `trackma/ui/web/assets`.
Use `?mock=1` when opening a production build in a regular browser without the
desktop bridge.
