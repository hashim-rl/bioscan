package org.bioscan.camera;

import android.app.Activity;
import android.app.Application;
import android.app.Dialog;
import android.os.Bundle;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.camera.core.*;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.Lifecycle;
import androidx.lifecycle.LifecycleOwner;
import androidx.lifecycle.LifecycleRegistry;
import com.google.common.util.concurrent.ListenableFuture;
import java.io.File;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;

/** Native camera only: no Python/NumPy work in the preview stream. */
public final class ScanCamera implements LifecycleOwner, Application.ActivityLifecycleCallbacks {
    public interface Listener {
        void onCaptured(String path, int width, int height, float x, float y, float w, float h);
        void onCancelled();
        void onError(String message);
    }
    private final Activity activity;
    private final Listener listener;
    private final LifecycleRegistry lifecycle = new LifecycleRegistry(this);
    private final Executor main;
    private Dialog dialog;
    private PreviewView previewView;
    private Guide guide;
    private TextView status;
    private Button shutter;
    private ProcessCameraProvider provider;
    private Camera camera;
    private Preview preview;
    private ImageCapture capture;
    private boolean closed = false, busy = false;
    private File pendingFile;

    public ScanCamera(Activity activity, Listener listener) {
        this.activity = activity; this.listener = listener;
        main = ContextCompat.getMainExecutor(activity);
    }
    @NonNull public Lifecycle getLifecycle() { return lifecycle; }
    private int dp(float n) { return Math.round(n * activity.getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size) {
        TextView t = new TextView(activity); t.setText(value); t.setTextSize(size);
        t.setTextColor(Color.WHITE); t.setGravity(Gravity.CENTER); return t;
    }
    public void open(String title, float widthRatio, float heightRatio) {
        activity.runOnUiThread(() -> {
            if (closed) return;
            try {
                lifecycle.setCurrentState(Lifecycle.State.CREATED);
                activity.getApplication().registerActivityLifecycleCallbacks(this);
                dialog = new Dialog(activity, android.R.style.Theme_Material_NoActionBar);
                dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
                LinearLayout root = new LinearLayout(activity);
                root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(Color.rgb(15,23,35));
                LinearLayout header = new LinearLayout(activity);
                Button back = new Button(activity); back.setText("Back");
                back.setOnClickListener(v -> cancel());
                header.addView(back, new LinearLayout.LayoutParams(dp(80), dp(52)));
                header.addView(text(title, 20), new LinearLayout.LayoutParams(0, dp(52), 1));
                root.addView(header);
                root.addView(text("Place inside guide. Tap to focus.", 15), new LinearLayout.LayoutParams(-1, dp(40)));
                FrameLayout frame = new FrameLayout(activity);
                previewView = new PreviewView(activity);
                previewView.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
                previewView.setScaleType(PreviewView.ScaleType.FILL_CENTER);
                frame.addView(previewView, new FrameLayout.LayoutParams(-1, -1));
                guide = new Guide(widthRatio, heightRatio);
                frame.addView(guide, new FrameLayout.LayoutParams(-1, -1));
                guide.setOnTouchListener((v, event) -> {
                    if (event.getAction() == MotionEvent.ACTION_UP && !busy) focus(event.getX(), event.getY(), false);
                    return true;
                });
                root.addView(frame, new LinearLayout.LayoutParams(-1, 0, 1));
                status = text("Opening back camera…", 15);
                root.addView(status, new LinearLayout.LayoutParams(-1, dp(58)));
                shutter = new Button(activity); shutter.setText("CAPTURE SCAN"); shutter.setTextSize(18);
                shutter.setEnabled(false); shutter.setOnClickListener(v -> {
                    if (!busy && camera != null) { busy=true; shutter.setEnabled(false);
                        focus(previewView.getWidth()/2f, previewView.getHeight()/2f, true); }
                });
                LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(-1, dp(64));
                buttonParams.setMargins(dp(20), 0, dp(20), dp(16)); root.addView(shutter, buttonParams);
                dialog.setContentView(root);
                dialog.setOnCancelListener(d -> cancel());
                dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                dialog.show(); dialog.getWindow().setLayout(-1, -1);
                lifecycle.setCurrentState(Lifecycle.State.RESUMED);
                previewView.post(this::bind);
            } catch (Exception e) { fail(e); }
        });
    }
    private void bind() {
        if (closed) return;
        ListenableFuture<ProcessCameraProvider> future = ProcessCameraProvider.getInstance(activity);
        future.addListener(() -> {
            if (closed) return;
            try {
                provider = future.get();
                int rotation = previewView.getDisplay().getRotation();
                preview = new Preview.Builder().setTargetRotation(rotation).build();
                capture = new ImageCapture.Builder().setTargetRotation(rotation)
                    .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY).setJpegQuality(95).build();
                preview.setSurfaceProvider(previewView.getSurfaceProvider());
                ViewPort viewport = previewView.getViewPort();
                if (viewport == null) throw new IllegalStateException("Preview has no viewport");
                UseCaseGroup group = new UseCaseGroup.Builder().setViewPort(viewport)
                    .addUseCase(preview).addUseCase(capture).build();
                camera = provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, group);
                previewView.getPreviewStreamState().observe(this, state -> {
                    if (state == PreviewView.StreamState.STREAMING && !busy) {
                        shutter.setEnabled(true); status.setText("Hold steady • tap fingers to focus");
                    }
                });
                android.util.Log.i("BioScanCamera", "Bound native back camera viewport="+previewView.getWidth()+"x"+previewView.getHeight());
            } catch (Exception e) { fail(e); }
        }, main);
    }
    private void focus(float x, float y, boolean takePhoto) {
        if (closed || camera == null) return;
        MeteringPoint point = previewView.getMeteringPointFactory().createPoint(x, y);
        FocusMeteringAction action = new FocusMeteringAction.Builder(point,
            FocusMeteringAction.FLAG_AF | FocusMeteringAction.FLAG_AE)
            .setAutoCancelDuration(3, TimeUnit.SECONDS).build();
        status.setText("Focusing… hold steady");
        ListenableFuture<FocusMeteringResult> future = camera.getCameraControl().startFocusAndMetering(action);
        future.addListener(() -> {
            if (closed) return;
            try {
                boolean sharp = future.get().isFocusSuccessful();
                android.util.Log.i("BioScanCamera", "Focus success="+sharp);
                status.setText(sharp ? "Focus locked" : "Focus not confirmed • adjust distance and retry");
                // CameraX still-capture runs its own 3A; DIP checks actual sharpness afterwards.
                if (takePhoto) save();
            } catch (Exception e) {
                busy=false; shutter.setEnabled(true); status.setText("Focus interrupted. Tap to retry.");
                android.util.Log.w("BioScanCamera", "Focus failed", e);
            }
        }, main);
    }
    private void save() {
        if (closed) return;
        try {
            final File file = File.createTempFile("bioscan-", ".jpg", activity.getCacheDir());
            pendingFile = file;
            final int width = previewView.getWidth(), height = previewView.getHeight();
            final RectF bounds = guide.bounds();
            status.setText("Capturing…");
            capture.takePicture(new ImageCapture.OutputFileOptions.Builder(file).build(), main,
                new ImageCapture.OnImageSavedCallback() {
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults result) {
                        if (closed) { file.delete(); return; }
                        pendingFile = null;
                        android.util.Log.i("BioScanCamera", "JPEG saved bytes="+file.length()+" guide="+bounds);
                        closeInternal();
                        listener.onCaptured(file.getAbsolutePath(), width, height,
                            bounds.left, bounds.top, bounds.width(), bounds.height());
                    }
                    public void onError(@NonNull ImageCaptureException error) { file.delete(); fail(error); }
                });
        } catch (Exception e) { fail(e); }
    }
    private void fail(Exception e) {
        if (closed) return;
        android.util.Log.e("BioScanCamera", "Camera failure", e);
        closeInternal(); listener.onError(e.toString());
    }
    private void cancel() { if (!closed) { closeInternal(); listener.onCancelled(); } }
    public void close() { activity.runOnUiThread(this::closeInternal); }
    private void closeInternal() {
        if (closed) return; closed=true;
        lifecycle.setCurrentState(Lifecycle.State.DESTROYED);
        if (provider != null && preview != null && capture != null) provider.unbind(preview, capture);
        if (dialog != null) dialog.dismiss();
        if (pendingFile != null) pendingFile.delete();
        activity.getApplication().unregisterActivityLifecycleCallbacks(this);
    }
    public void onActivityResumed(Activity a) { if(a==activity && !closed) lifecycle.setCurrentState(Lifecycle.State.RESUMED); }
    public void onActivityPaused(Activity a) { if(a==activity && !closed) lifecycle.setCurrentState(Lifecycle.State.CREATED); }
    public void onActivityDestroyed(Activity a) { if(a==activity) closeInternal(); }
    public void onActivityCreated(Activity a, Bundle b) {}
    public void onActivityStarted(Activity a) {}
    public void onActivityStopped(Activity a) {}
    public void onActivitySaveInstanceState(Activity a, Bundle b) {}

    private final class Guide extends View {
        private final float wr, hr;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        Guide(float w, float h) { super(activity); wr=w; hr=h; }
        RectF bounds() {
            float w=getWidth()*wr, h=getHeight()*hr;
            return new RectF((getWidth()-w)/2, (getHeight()-h)/2, (getWidth()+w)/2, (getHeight()+h)/2);
        }
        protected void onDraw(Canvas canvas) {
            RectF b=bounds(); paint.setStyle(Paint.Style.FILL); paint.setColor(0x88000000);
            canvas.drawRect(0,0,getWidth(),b.top,paint); canvas.drawRect(0,b.bottom,getWidth(),getHeight(),paint);
            canvas.drawRect(0,b.top,b.left,b.bottom,paint); canvas.drawRect(b.right,b.top,getWidth(),b.bottom,paint);
            paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(dp(2)); paint.setColor(0xff46e9a5);
            canvas.drawRoundRect(b,dp(12),dp(12),paint);
        }
    }
}
