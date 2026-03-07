import os
import json
from copy import deepcopy
from pathlib import Path
from threading import Lock, Thread, Event
from typing import Dict, Optional
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from logic.scripts.download_image import download_nature_image
from logic.scripts.download_quran_video import download_quran_video
from logic.scripts.extract_text_from_video import extract_text_from_video
from logic.scripts.create_final_video import create_final_video
from logic.scripts.post_to_instagram import post_to_instagram

app = Flask(__name__)

# Global stop event for canceling operations
stop_event = Event()

# Cronjob scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Settings file path
SETTINGS_FILE = 'assets/settings.json'

# Canonical defaults used for first run and reset-to-default operations
DEFAULT_SETTINGS = {
    'default_channel_url': 'https://www.youtube.com/@Am9li9/videos',
    'default_keyword': 'سورة',
    'default_caption': '⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين',
    'default_image_path': None,
    'cronjob_enabled': False,
    'cronjob_interval_hours': 24,
    'cronjob_time': '09:00',
}

# Ensure required directories exist
os.makedirs('assets', exist_ok=True)
os.makedirs('output', exist_ok=True)


def load_settings():
    """Load settings from JSON file"""
    if not Path(SETTINGS_FILE).exists():
        return deepcopy(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            merged = deepcopy(DEFAULT_SETTINGS)
            if isinstance(saved, dict):
                merged.update(saved)
            return merged
    except Exception:
        return deepcopy(DEFAULT_SETTINGS)


def save_settings(settings):
    """Save settings to JSON file"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

# Store pipeline state
pipeline_state: Dict[str, Optional[str]] = {
    'image_path': None,
    'video_path': None,
    'video_title': None,
    'text_overlay_path': None,
    'final_video_path': None,
}

progress_lock = Lock()


def _new_progress_state():
    return {
        'active': False,
        'mode': None,
        'overall_percent': 0.0,
        'overall_message': '',
        'current_step': None,
        'step_order': [],
        'steps': {},
    }


progress_state = _new_progress_state()


def _recalculate_overall_locked():
    step_order = progress_state.get('step_order', [])
    if not step_order:
        progress_state['overall_percent'] = 0.0
        return

    total = len(step_order)
    score = 0.0

    for step in step_order:
        data = progress_state['steps'].get(step, {})
        status = data.get('status')
        if status in ('completed', 'skipped'):
            score += 1.0
        elif status == 'processing':
            score += max(0.0, min(100.0, float(data.get('progress', 0.0)))) / 100.0

    progress_state['overall_percent'] = round((score / total) * 100.0, 1)


def _reset_progress(mode, step_order):
    with progress_lock:
        progress_state.clear()
        progress_state.update(_new_progress_state())
        progress_state['active'] = True
        progress_state['mode'] = mode
        progress_state['step_order'] = list(step_order)
        progress_state['steps'] = {
            step: {
                'status': 'pending',
                'progress': 0.0,
                'message': '',
                'result': None,
            }
            for step in step_order
        }
        _recalculate_overall_locked()


def _set_step(step, *, status=None, progress=None, message=None, result=None):
    with progress_lock:
        if step not in progress_state.get('steps', {}):
            progress_state['steps'][step] = {
                'status': 'pending',
                'progress': 0.0,
                'message': '',
                'result': None,
            }
            progress_state['step_order'].append(step)

        data = progress_state['steps'][step]
        if status is not None:
            data['status'] = status
        if progress is not None:
            data['progress'] = round(max(0.0, min(100.0, float(progress))), 1)
        if message is not None:
            data['message'] = message
        if result is not None:
            data['result'] = result

        progress_state['current_step'] = step
        if message:
            progress_state['overall_message'] = message

        _recalculate_overall_locked()


def _finalize_progress(message='Done'):
    with progress_lock:
        progress_state['active'] = False
        progress_state['current_step'] = None
        progress_state['overall_message'] = message
        _recalculate_overall_locked()


@app.route('/')
def welcome():
    return render_template('main.html')


@app.route('/api/download-image', methods=['POST'])
def api_download_image():
    """Download a nature image from Unsplash"""
    try:
        data = request.get_json() or {}
        query = data.get('query', 'nature landscape')
        
        image_path = download_nature_image(
            output_path='assets/nature_image.jpg',
            query=query
        )
        
        if image_path:
            pipeline_state['image_path'] = image_path
            return jsonify({
                'success': True,
                'message': 'Image downloaded successfully',
                'path': image_path,
                'preview_url': f'/api/preview/image'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to download image'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/download-video', methods=['POST'])
def api_download_video():
    """Download a Quran video from YouTube"""
    try:
        data = request.get_json() or {}
        channel_url = data.get('channel_url', 'https://www.youtube.com/@Am9li9/videos')
        keyword = data.get('keyword', 'سورة')
        video_url = data.get('video_url')
        
        video_path, video_title, meta = download_quran_video(
            channel_url=channel_url,
            output_path='assets/quran_video.mp4',
            title_keyword=keyword,
            video_url=video_url,
        )
        
        if video_path:
            pipeline_state['video_path'] = video_path
            pipeline_state['video_title'] = video_title
            return jsonify({
                'success': True,
                'message': f'Video downloaded: {video_title}',
                'path': video_path,
                'title': video_title,
                'preview_url': f'/api/preview/video'
            })
        else:
            message = meta.get('message') if isinstance(meta, dict) else None
            return jsonify({
                'success': False,
                'message': message or 'Failed to download video',
                'duplicate': bool(meta.get('duplicate')) if isinstance(meta, dict) else False,
            }), 409 if isinstance(meta, dict) and meta.get('duplicate') else 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/extract-text', methods=['POST'])
def api_extract_text():
    """Extract transparent text overlay from video"""
    try:
        video_path = pipeline_state.get('video_path')
        
        if not video_path:
            return jsonify({
                'success': False,
                'message': 'No video available. Please download a video first.'
            }), 400
        
        text_overlay_path = extract_text_from_video(
            video_path=video_path,
            output_path='assets/quran_text_frame.mov'
        )
        
        if text_overlay_path:
            pipeline_state['text_overlay_path'] = text_overlay_path
            return jsonify({
                'success': True,
                'message': 'Text overlay extracted successfully',
                'path': text_overlay_path,
                'preview_url': f'/api/preview/overlay'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to extract text overlay'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/create-final', methods=['POST'])
def api_create_final():
    """Create final video with image background and text overlay"""
    try:
        image_path = pipeline_state.get('image_path')
        video_path = pipeline_state.get('video_path')
        text_overlay_path = pipeline_state.get('text_overlay_path')
        
        if not image_path:
            return jsonify({
                'success': False,
                'message': 'No image available. Please download an image first.'
            }), 400
        
        if not video_path:
            return jsonify({
                'success': False,
                'message': 'No video available. Please download a video first.'
            }), 400
        
        _reset_progress('create-final', ['final'])
        _set_step('final', status='processing', progress=0, message='Creating final video...')

        final_video_path = create_final_video(
            image_path=image_path,
            quran_video_path=video_path,
            text_frame_path=text_overlay_path,
            output_path='output/final_output.mp4',
            progress_callback=lambda percent, msg: _set_step('final', status='processing', progress=percent, message=msg),
        )
        
        if final_video_path:
            pipeline_state['final_video_path'] = final_video_path
            _set_step('final', status='completed', progress=100, message='Final video created successfully', result={
                'path': final_video_path,
                'preview_url': '/api/preview/final',
            })
            _finalize_progress('Final video created successfully')
            return jsonify({
                'success': True,
                'message': 'Final video created successfully',
                'path': final_video_path,
                'preview_url': f'/api/preview/final'
            })
        else:
            _set_step('final', status='error', message='Failed to create final video')
            _finalize_progress('Failed to create final video')
            return jsonify({
                'success': False,
                'message': 'Failed to create final video'
            }), 500
    except Exception as e:
        _set_step('final', status='error', message=f'Error: {str(e)}')
        _finalize_progress('Final video creation failed')
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/post-instagram', methods=['POST'])
def api_post_instagram():
    """Post final video to Instagram"""
    try:
        data = request.get_json() or {}
        caption = data.get('caption', '')
        
        final_video_path = pipeline_state.get('final_video_path')
        
        if not final_video_path:
            return jsonify({
                'success': False,
                'message': 'No final video available. Please create the final video first.'
            }), 400
        
        if not caption:
            video_title = pipeline_state.get('video_title', '')
            if video_title:
                caption = f"{video_title}\n\n#Quran #Islam #QuranVerses #DailyReminder #Faith #Peace"
            else:
                caption = "⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين"
        
        thumbnail_path = pipeline_state.get('image_path') or 'assets/nature_image.jpg'
        
        success = post_to_instagram(
            video_path=final_video_path,
            caption=caption,
            thumbnail_path=thumbnail_path
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Video posted to Instagram successfully! 🎉'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to post to Instagram'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


def _scheduled_pipeline_job():
    """Scheduled cronjob that runs the pipeline automatically"""
    print(f"[CRONJOB] Starting scheduled pipeline at {datetime.now()}")
    settings = load_settings()
    
    # Use saved settings for the pipeline
    channel_url = settings.get('default_channel_url', 'https://www.youtube.com/@Am9li9/videos')
    keyword = settings.get('default_keyword', 'سورة')
    caption = settings.get('default_caption', '')
    
    # Run pipeline with retry logic (retry for the current day only)
    max_retries = 5
    retry_count = 0
    start_date = datetime.now().date()
    
    while retry_count < max_retries:
        # Check if we're still on the same day
        if datetime.now().date() != start_date:
            print(f"[CRONJOB] Day changed, stopping retries for previous day")
            break
        
        if retry_count > 0:
            print(f"[CRONJOB] Retry attempt {retry_count}/{max_retries}")
        
        try:
            # Reset stop event before running
            stop_event.clear()
            _run_full_pipeline_bg(skip_text_overlay=False, auto_post=True, caption=caption, 
                                  channel_url=channel_url, keyword=keyword, video_url=None, is_cronjob=True)
            
            # Check if pipeline completed successfully
            with progress_lock:
                if progress_state.get('overall_percent') == 100.0:
                    print(f"[CRONJOB] Pipeline completed successfully")
                    return
        except Exception as e:
            print(f"[CRONJOB] Pipeline failed with error: {e}")
        
        retry_count += 1
        if retry_count < max_retries:
            import time
            time.sleep(300)  # Wait 5 minutes before retry
    
    print(f"[CRONJOB] Pipeline failed after {retry_count} attempts")


def configure_cronjob():
    """Configure and schedule the cronjob based on settings"""
    settings = load_settings()
    
    # Remove all existing jobs
    scheduler.remove_all_jobs()
    
    if not settings.get('cronjob_enabled', False):
        print("[CRONJOB] Cronjob is disabled")
        return
    
    interval_hours = settings.get('cronjob_interval_hours', 24)
    job_time = settings.get('cronjob_time', '09:00')
    
    try:
        hour, minute = map(int, job_time.split(':'))
        
        # Schedule job at specific time, repeating every X hours
        if interval_hours == 24:
            # Once per day at specific time
            trigger = CronTrigger(hour=hour, minute=minute)
        else:
            # Every X hours starting at specific time
            trigger = CronTrigger(hour=f'*/{interval_hours}', minute=minute)
        
        scheduler.add_job(_scheduled_pipeline_job, trigger, id='pipeline_cronjob', replace_existing=True)
        print(f"[CRONJOB] Scheduled to run every {interval_hours} hours starting at {job_time}")
    except Exception as e:
        print(f"[CRONJOB] Error configuring cronjob: {e}")


def _run_full_pipeline_bg(skip_text_overlay, auto_post, caption, channel_url, keyword, video_url, is_cronjob=False):
    """Background task for full pipeline execution"""
    step_order = ['image', 'video', 'overlay', 'final'] + (['post'] if auto_post else [])
    _reset_progress('full-pipeline', step_order)
    
    try:
        # Step 1: Download image
        if stop_event.is_set():
            _finalize_progress('Pipeline cancelled by user')
            return
            
        _set_step('image', status='processing', progress=0, message='Downloading image...')
        
        # Check if using default image
        settings = load_settings()
        default_image = settings.get('default_image_path')
        
        if default_image and Path(default_image).exists():
            image_path = default_image
            print(f"Using default image: {image_path}")
        else:
            image_path = download_nature_image()
        
        if not image_path:
            _set_step('image', status='error', message='Failed to download image')
            _finalize_progress('Pipeline failed at image step')
            return
        pipeline_state['image_path'] = image_path
        image_result = {
            'step': 'image',
            'success': True,
            'message': 'Image downloaded successfully',
            'preview_url': '/api/preview/image',
        }
        _set_step('image', status='completed', progress=100, message=image_result['message'], result=image_result)
        
        # Step 2: Download video
        if stop_event.is_set():
            _finalize_progress('Pipeline cancelled by user')
            return
            
        _set_step('video', status='processing', progress=0, message='Downloading video...')
        video_path, video_title, video_meta = download_quran_video(
            channel_url=channel_url,
            title_keyword=keyword,
            video_url=video_url,
        )
        if not video_path:
            video_error = video_meta.get('message') if isinstance(video_meta, dict) else 'Failed to download video'
            _set_step('video', status='error', message=video_error)
            _finalize_progress('Pipeline failed at video step')
            return
        pipeline_state['video_path'] = video_path
        pipeline_state['video_title'] = video_title
        video_result = {
            'step': 'video',
            'success': True,
            'message': f'Video downloaded: {video_title}',
            'preview_url': '/api/preview/video',
        }
        _set_step('video', status='completed', progress=100, message=video_result['message'], result=video_result)
        
        # Step 3: Extract text overlay (optional)
        if stop_event.is_set():
            _finalize_progress('Pipeline cancelled by user')
            return
            
        text_overlay_path = None
        if not skip_text_overlay:
            _set_step('overlay', status='processing', progress=0, message='Extracting text overlay...')
            text_overlay_path = extract_text_from_video(video_path)
            if text_overlay_path:
                pipeline_state['text_overlay_path'] = text_overlay_path
                overlay_result = {
                    'step': 'overlay',
                    'success': True,
                    'message': 'Text overlay extracted successfully',
                    'preview_url': '/api/preview/overlay',
                }
                _set_step('overlay', status='completed', progress=100, message=overlay_result['message'], result=overlay_result)
            else:
                pipeline_state['text_overlay_path'] = None
                overlay_result = {
                    'step': 'overlay',
                    'success': False,
                    'message': 'Text overlay extraction failed. Continuing without overlay.',
                }
                _set_step('overlay', status='error', progress=100, message=overlay_result['message'], result=overlay_result)
                text_overlay_path = None
        else:
            overlay_result = {
                'step': 'overlay',
                'success': True,
                'message': 'Overlay step skipped by user option',
            }
            _set_step('overlay', status='skipped', progress=100, message=overlay_result['message'], result=overlay_result)
        
        # Step 4: Create final video
        if stop_event.is_set():
            _finalize_progress('Pipeline cancelled by user')
            return
            
        _set_step('final', status='processing', progress=0, message='Creating final video...')
        final_video_path = create_final_video(
            image_path,
            video_path,
            text_overlay_path,
            progress_callback=lambda percent, msg: _set_step('final', status='processing', progress=percent, message=msg),
        )
        if not final_video_path:
            _set_step('final', status='error', message='Failed to create final video')
            _finalize_progress('Pipeline failed at final step')
            return
        pipeline_state['final_video_path'] = final_video_path
        final_result = {
            'step': 'final',
            'success': True,
            'message': 'Final video created successfully',
            'preview_url': '/api/preview/final',
        }
        _set_step('final', status='completed', progress=100, message=final_result['message'], result=final_result)
        
        # Step 5: Post to Instagram (optional)
        if auto_post:
            if stop_event.is_set():
                _finalize_progress('Pipeline cancelled by user')
                return
                
            _set_step('post', status='processing', progress=0, message='Posting to Instagram...')
            if not caption:
                caption = f"{video_title}\n\n#Quran #Islam #QuranVerses" if video_title else "Daily Quran verse"
            
            success = post_to_instagram(final_video_path, caption, pipeline_state.get('image_path') or 'assets/nature_image.jpg')
            if not success:
                post_result = {
                    'step': 'post',
                    'success': False,
                    'message': 'Pipeline completed but posting failed',
                }
                _set_step('post', status='error', progress=100, message=post_result['message'], result=post_result)
                _finalize_progress('Pipeline completed with post failure')
                return
            post_result = {
                'step': 'post',
                'success': True,
                'message': 'Video posted to Instagram successfully',
            }
            _set_step('post', status='completed', progress=100, message=post_result['message'], result=post_result)
        
        _finalize_progress('Pipeline completed successfully')
    except Exception as e:
        print(f"Background pipeline error: {e}")
        _finalize_progress(f'Pipeline failed: {str(e)}')


@app.route('/api/run-full-pipeline', methods=['POST'])
def api_run_full_pipeline():
    """Run the complete pipeline from start to finish (non-blocking)"""
    try:
        data = request.get_json() or {}
        skip_text_overlay = data.get('skip_text_overlay', False)
        auto_post = data.get('auto_post', False)
        caption = data.get('caption', '')
        channel_url = data.get('channel_url', 'https://www.youtube.com/@Am9li9/videos')
        keyword = data.get('keyword', 'سورة')
        video_url = data.get('video_url')

        # Reset stop event
        stop_event.clear()

        bg_thread = Thread(
            target=_run_full_pipeline_bg,
            args=(skip_text_overlay, auto_post, caption, channel_url, keyword, video_url, False),
            daemon=True
        )
        bg_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Pipeline started. Monitor progress via /api/progress endpoint.',
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/progress')
def api_progress():
    """Get live progress for long-running operations"""
    with progress_lock:
        snapshot = deepcopy(progress_state)
    return jsonify(snapshot)


@app.route('/api/preview/<media_type>')
def api_preview(media_type):
    """Serve media files for preview"""
    try:
        if media_type == 'image':
            path = pipeline_state.get('image_path', 'assets/nature_image.jpg')
        elif media_type == 'video':
            path = pipeline_state.get('video_path', 'assets/quran_video.mp4')
        elif media_type == 'overlay':
            path = pipeline_state.get('text_overlay_path', 'assets/quran_text_frame.mov')
        elif media_type == 'final':
            path = pipeline_state.get('final_video_path', 'output/final_output.mp4')
        else:
            return jsonify({'error': 'Invalid media type'}), 400
        
        if path and Path(path).exists():
            return send_file(path)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/state')
def api_state():
    """Get current pipeline state"""
    return jsonify({
        'has_image': pipeline_state.get('image_path') is not None,
        'has_video': pipeline_state.get('video_path') is not None,
        'has_overlay': pipeline_state.get('text_overlay_path') is not None,
        'has_final': pipeline_state.get('final_video_path') is not None,
        'video_title': pipeline_state.get('video_title'),
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset pipeline state"""
    pipeline_state.clear()
    pipeline_state.update({
        'image_path': None,
        'video_path': None,
        'video_title': None,
        'text_overlay_path': None,
        'final_video_path': None,
    })
    return jsonify({'success': True, 'message': 'Pipeline state reset'})


@app.route('/api/reset-downloaded-videos', methods=['POST'])
def api_reset_downloaded_videos():
    """Clear downloaded video IDs tracking list"""
    try:
        downloaded_file = Path('assets/downloaded_videos.txt')
        downloaded_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_file.write_text('', encoding='utf-8')
        return jsonify({'success': True, 'message': 'Downloaded videos list has been reset'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/stop-all', methods=['POST'])
def api_stop_all():
    """Stop all running processes"""
    try:
        stop_event.set()
        return jsonify({'success': True, 'message': 'Stop signal sent to all running processes'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update user settings"""
    if request.method == 'GET':
        settings = load_settings()
        return jsonify({'success': True, 'settings': settings})
    else:
        try:
            data = request.get_json() or {}
            settings = load_settings()
            settings.update(data)
            
            if save_settings(settings):
                # Reconfigure cronjob if settings changed
                if 'cronjob_enabled' in data or 'cronjob_interval_hours' in data or 'cronjob_time' in data:
                    configure_cronjob()
                
                return jsonify({'success': True, 'message': 'Settings saved successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to save settings'}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/settings/reset-default', methods=['POST'])
def api_settings_reset_default():
    """Reset one setting key to its predefined default value"""
    try:
        data = request.get_json() or {}
        key = data.get('key')
        if key not in DEFAULT_SETTINGS:
            return jsonify({'success': False, 'message': 'Invalid settings key'}), 400

        settings = load_settings()
        settings[key] = deepcopy(DEFAULT_SETTINGS[key])

        if not save_settings(settings):
            return jsonify({'success': False, 'message': 'Failed to save settings'}), 500

        if key in ('cronjob_enabled', 'cronjob_interval_hours', 'cronjob_time'):
            configure_cronjob()

        return jsonify({
            'success': True,
            'message': f'{key} reset to default',
            'key': key,
            'value': settings.get(key),
            'settings': settings,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/upload-image', methods=['POST'])
def api_upload_image():
    """Upload a custom image"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Save the uploaded image
        upload_path = 'assets/custom_image.jpg'
        file.save(upload_path)
        
        # Optionally save as default
        save_as_default = request.form.get('save_as_default') == 'true'
        if save_as_default:
            settings = load_settings()
            settings['default_image_path'] = upload_path
            save_settings(settings)
        
        # Update pipeline state
        pipeline_state['image_path'] = upload_path
        
        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'path': upload_path,
            'preview_url': '/api/preview/custom',
            'saved_as_default': save_as_default
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/preview/custom')
def api_preview_custom():
    """Serve custom uploaded image"""
    try:
        path = 'assets/custom_image.jpg'
        if Path(path).exists():
            return send_file(path)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cronjob/status', methods=['GET'])
def api_cronjob_status():
    """Get cronjob status"""
    try:
        settings = load_settings()
        jobs = scheduler.get_jobs()
        
        return jsonify({
            'success': True,
            'enabled': settings.get('cronjob_enabled', False),
            'interval_hours': settings.get('cronjob_interval_hours', 24),
            'time': settings.get('cronjob_time', '09:00'),
            'active_jobs': len(jobs),
            'next_run': str(jobs[0].next_run_time) if jobs else None
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/cronjob/configure', methods=['POST'])
def api_cronjob_configure():
    """Configure and start/stop cronjob"""
    try:
        data = request.get_json() or {}
        settings = load_settings()
        
        if 'enabled' in data:
            settings['cronjob_enabled'] = data['enabled']
        if 'interval_hours' in data:
            settings['cronjob_interval_hours'] = data['interval_hours']
        if 'time' in data:
            settings['cronjob_time'] = data['time']
        
        save_settings(settings)
        configure_cronjob()
        
        return jsonify({'success': True, 'message': 'Cronjob configured successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# Initialize cronjob on startup
configure_cronjob()


if __name__ == '__main__':
    # Bind to 0.0.0.0 for cloud deployment, localhost for development
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    app.run(host=host, port=port, debug=False)
    app.run(debug=True, port=5000)