import os
import zipfile
import shutil
import pydicom
import nibabel as nib
import numpy as np
from flask import Flask, request, redirect, url_for, render_template

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
PROCESSED_FOLDER = 'processed/'
ALLOWED_EXTENSIONS = {'zip'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER


def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_zip(file_path, extract_to):
    """Extrae el archivo ZIP en el directorio especificado."""
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def check_dicom_file(file_path):
    """Verifica si un archivo es DICOM y maneja la lectura."""
    try:
        dicom_data = pydicom.dcmread(file_path, force=True)
        return dicom_data
    except pydicom.errors.InvalidDicomError:
        return None
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None


def get_dicom_series(directory):
    """Obtiene y organiza archivos DICOM por nombre de carpeta (paciente) y número de serie."""
    series_files = {}
    for root, dirs, files in os.walk(directory):
        if not files:
            continue
        patient_folder = os.path.basename(root)
        if patient_folder not in series_files:
            series_files[patient_folder] = {}
        for file in files:
            file_path = os.path.join(root, file)
            print(f"Procesando archivo: {file_path}")
            dicom_data = check_dicom_file(file_path)
            if dicom_data:
                series_number = dicom_data.get('SeriesNumber', 'Unknown')
                if series_number not in series_files[patient_folder]:
                    series_files[patient_folder][series_number] = []
                series_files[patient_folder][series_number].append(file_path)
            else:
                print(f"Archivo no reconocido como DICOM: {file_path}")
    return series_files


def dicom_to_nifti(dicom_files, nifti_file_path):
    """Convierte una lista de archivos DICOM a un archivo NIfTI."""
    slices = []
    for dicom_file in dicom_files:
        if not os.path.exists(dicom_file):
            print(f"Archivo DICOM no encontrado: {dicom_file}")
            continue
        dicom_data = pydicom.dcmread(dicom_file, force=True)
        slices.append(dicom_data.pixel_array)

    if slices:
        # Ordenar las imágenes por el atributo InstanceNumber (si disponible)
        slices = sorted(slices, key=lambda x: dicom_data.InstanceNumber)
        volume = np.stack(slices, axis=-1)
        nifti_img = nib.Nifti1Image(volume, affine=np.eye(4))
        nib.save(nifti_img, nifti_file_path)
        print(f"Archivo NIfTI guardado en: {nifti_file_path}")


def delete_dicom_files(directory):
    """Elimina todos los archivos DICOM en el directorio especificado, excepto los archivos NIfTI (.nii)."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Eliminar solo archivos que no tengan la extensión .nii
                if not file_path.endswith('.nii') and os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Archivo DICOM eliminado: {file_path}")
                else:
                    print(f"Archivo no encontrado o no es DICOM (o es un archivo NIfTI): {file_path}")
            except Exception as e:
                print(f"Error al eliminar el archivo DICOM: {e}")

def process_zip(zip_path):
    """Procesa el archivo ZIP, organiza los archivos DICOM por paciente y número de serie, y convierte cada serie a NIfTI."""
    extract_zip(zip_path, app.config['UPLOAD_FOLDER'])
    series_files = get_dicom_series(app.config['UPLOAD_FOLDER'])

    # Eliminar el archivo ZIP después de procesar
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"Archivo ZIP eliminado: {zip_path}")

    # Crear la carpeta para guardar los archivos ordenados
    if not os.path.exists(app.config['PROCESSED_FOLDER']):
        os.makedirs(app.config['PROCESSED_FOLDER'])

    for patient_name, series_dict in series_files.items():
        patient_folder = os.path.join(app.config['PROCESSED_FOLDER'], f"Patient_{patient_name}")
        if not os.path.exists(patient_folder):
            os.makedirs(patient_folder)
        for series_number, files in series_dict.items():
            # Convertir la serie de DICOM a NIfTI y guardar en la carpeta del paciente
            nifti_file_path = os.path.join(patient_folder, f"Series_{series_number}.nii")
            dicom_to_nifti(files, nifti_file_path)

        # Eliminar todos los DICOMs después de convertir
        delete_dicom_files(patient_folder)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Muestra el formulario de carga y maneja el archivo cargado."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file and allowed_file(file.filename):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            print(f"Archivo guardado en: {file_path}")  # Línea de depuración
            process_zip(file_path)
            return redirect(url_for('uploaded_file', filename=file.filename))
    return render_template('index.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Muestra un mensaje de confirmación después de procesar el archivo."""
    return f'Archivo {filename} procesado y ordenado.'


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['PROCESSED_FOLDER']):
        os.makedirs(app.config['PROCESSED_FOLDER'])
    app.run(debug=True)
