package com.exemple.explorateur

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.webkit.MimeTypeMap
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.text.DecimalFormat

class MainActivity : AppCompatActivity() {

    private lateinit var listView: ListView
    private lateinit var pathLabel: TextView
    private lateinit var emptyLabel: TextView
    private lateinit var searchInput: EditText
    private lateinit var newFolderButton: Button
    private lateinit var pasteButton: Button

    private val racine: File = Environment.getExternalStorageDirectory()
    private var courant: File = racine
    private var entreesCompletes: List<File> = emptyList()
    private var entreesAffichees: List<File> = emptyList()

    private var pressePapiers: File? = null
    private var couperMode: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        listView = findViewById(R.id.listView)
        pathLabel = findViewById(R.id.pathLabel)
        emptyLabel = findViewById(R.id.emptyLabel)
        searchInput = findViewById(R.id.searchInput)
        newFolderButton = findViewById(R.id.newFolderButton)
        pasteButton = findViewById(R.id.pasteButton)

        listView.setOnItemClickListener { _, _, position, _ ->
            val cible = entreesAffichees[position]
            if (cible.isDirectory) ouvrirDossier(cible) else ouvrirFichier(cible)
        }

        listView.setOnItemLongClickListener { _, _, position, _ ->
            menuContextuel(entreesAffichees[position])
            true
        }

        newFolderButton.setOnClickListener { dialogueNouveauDossier() }
        pasteButton.setOnClickListener { coller() }

        searchInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                appliquerFiltre()
            }
        })

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (searchInput.text.isNotEmpty()) {
                    searchInput.setText("")
                    return
                }
                val parent = courant.parentFile
                if (parent != null && courant.absolutePath != racine.absolutePath) {
                    ouvrirDossier(parent)
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        demanderPermission()
    }

    // -- Permissions ----------------------------------------------------------

    private fun demanderPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                AlertDialog.Builder(this)
                    .setTitle(R.string.permission_titre)
                    .setMessage(R.string.permission_message)
                    .setPositiveButton(R.string.ouvrir_reglages) { _, _ ->
                        val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        intent.data = Uri.parse("package:$packageName")
                        startActivity(intent)
                    }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
            } else {
                ouvrirDossier(courant)
            }
        } else {
            val permission = Manifest.permission.READ_EXTERNAL_STORAGE
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, arrayOf(permission), 1)
            } else {
                ouvrirDossier(courant)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && Environment.isExternalStorageManager()) {
            ouvrirDossier(courant)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            ouvrirDossier(courant)
        } else {
            Toast.makeText(this, R.string.permission_refusee, Toast.LENGTH_LONG).show()
        }
    }

    // -- Affichage ------------------------------------------------------------

    private fun ouvrirDossier(dossier: File) {
        courant = dossier
        pathLabel.text = dossier.absolutePath

        val tousFichiers = dossier.listFiles()?.toList() ?: emptyList()
        entreesCompletes = tousFichiers.sortedWith(
            compareByDescending<File> { it.isDirectory }.thenBy { it.name.lowercase() }
        )
        searchInput.setText("")
        appliquerFiltre()
    }

    private fun appliquerFiltre() {
        val filtre = searchInput.text.toString().trim().lowercase()
        entreesAffichees = if (filtre.isEmpty()) {
            entreesCompletes
        } else {
            entreesCompletes.filter { it.name.lowercase().contains(filtre) }
        }

        if (entreesAffichees.isEmpty()) {
            emptyLabel.visibility = View.VISIBLE
            listView.visibility = View.GONE
        } else {
            emptyLabel.visibility = View.GONE
            listView.visibility = View.VISIBLE
        }

        val libelles = entreesAffichees.map { afficherEntree(it) }
        listView.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, libelles)
    }

    private fun afficherEntree(fichier: File): String {
        return if (fichier.isDirectory) {
            "[D]  ${fichier.name}"
        } else {
            "      ${fichier.name}   (${tailleLisible(fichier.length())})"
        }
    }

    private fun tailleLisible(octets: Long): String {
        if (octets < 1024) return "$octets o"
        val unites = arrayOf("Kio", "Mio", "Gio", "Tio")
        var valeur = octets.toDouble() / 1024
        var i = 0
        while (valeur >= 1024 && i < unites.size - 1) {
            valeur /= 1024
            i++
        }
        return "${DecimalFormat("0.#").format(valeur)} ${unites[i]}"
    }

    private fun rafraichir() {
        ouvrirDossier(courant)
    }

    // -- Ouverture ------------------------------------------------------------

    private fun ouvrirFichier(fichier: File) {
        try {
            val uri: Uri = FileProvider.getUriForFile(
                this,
                "$packageName.fileprovider",
                fichier
            )
            val mime = MimeTypeMap.getSingleton()
                .getMimeTypeFromExtension(fichier.extension.lowercase())
                ?: "*/*"
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, mime)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(Intent.createChooser(intent, getString(R.string.ouvrir_avec)))
        } catch (e: Exception) {
            toast(getString(R.string.erreur_ouverture, e.message))
        }
    }

    // -- Menu contextuel ------------------------------------------------------

    private fun menuContextuel(fichier: File) {
        val actions = if (fichier.isDirectory) {
            arrayOf(
                getString(R.string.ouvrir),
                getString(R.string.renommer),
                getString(R.string.copier),
                getString(R.string.couper),
                getString(R.string.supprimer)
            )
        } else {
            arrayOf(
                getString(R.string.ouvrir),
                getString(R.string.partager),
                getString(R.string.renommer),
                getString(R.string.copier),
                getString(R.string.couper),
                getString(R.string.supprimer)
            )
        }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.action_pour, fichier.name))
            .setItems(actions) { _, index ->
                when (actions[index]) {
                    getString(R.string.ouvrir) ->
                        if (fichier.isDirectory) ouvrirDossier(fichier) else ouvrirFichier(fichier)
                    getString(R.string.partager) -> partager(fichier)
                    getString(R.string.renommer) -> dialogueRenommer(fichier)
                    getString(R.string.copier) -> { pressePapiers = fichier; couperMode = false; majBoutonColler() }
                    getString(R.string.couper) -> { pressePapiers = fichier; couperMode = true; majBoutonColler() }
                    getString(R.string.supprimer) -> dialogueSupprimer(fichier)
                }
            }
            .setNegativeButton(R.string.annuler, null)
            .show()
    }

    private fun majBoutonColler() {
        pasteButton.visibility = if (pressePapiers != null) View.VISIBLE else View.GONE
        if (pressePapiers != null) {
            val verbe = if (couperMode) getString(R.string.couper) else getString(R.string.copier)
            toast("$verbe : ${pressePapiers!!.name}")
        }
    }

    // -- Actions --------------------------------------------------------------

    private fun partager(fichier: File) {
        try {
            val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", fichier)
            val mime = MimeTypeMap.getSingleton()
                .getMimeTypeFromExtension(fichier.extension.lowercase()) ?: "*/*"
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = mime
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, getString(R.string.partager)))
        } catch (e: Exception) {
            toast(getString(R.string.erreur_generique, e.message))
        }
    }

    private fun dialogueRenommer(fichier: File) {
        val champ = EditText(this).apply { setText(fichier.name) }
        AlertDialog.Builder(this)
            .setTitle(R.string.renommer)
            .setView(champ)
            .setPositiveButton(R.string.ok) { _, _ ->
                val nouveauNom = champ.text.toString().trim()
                if (nouveauNom.isEmpty() || nouveauNom == fichier.name) return@setPositiveButton
                val cible = File(fichier.parentFile, nouveauNom)
                if (cible.exists()) {
                    toast(getString(R.string.erreur_generique, "déjà présent"))
                    return@setPositiveButton
                }
                if (fichier.renameTo(cible)) {
                    toast(getString(R.string.renommage_termine))
                    rafraichir()
                } else {
                    toast(getString(R.string.erreur_generique, "renommage échoué"))
                }
            }
            .setNegativeButton(R.string.annuler, null)
            .show()
    }

    private fun dialogueSupprimer(fichier: File) {
        AlertDialog.Builder(this)
            .setTitle(R.string.confirmer_suppression)
            .setMessage(getString(R.string.supprimer_message, fichier.name))
            .setPositiveButton(R.string.supprimer) { _, _ ->
                val ok = fichier.deleteRecursively()
                if (ok) {
                    if (pressePapiers?.absolutePath == fichier.absolutePath) {
                        pressePapiers = null
                        majBoutonColler()
                    }
                    toast(getString(R.string.suppression_terminee))
                    rafraichir()
                } else {
                    toast(getString(R.string.erreur_generique, "suppression échouée"))
                }
            }
            .setNegativeButton(R.string.annuler, null)
            .show()
    }

    private fun dialogueNouveauDossier() {
        val champ = EditText(this).apply { hint = getString(R.string.nom) }
        AlertDialog.Builder(this)
            .setTitle(R.string.nouveau_dossier)
            .setView(champ)
            .setPositiveButton(R.string.ok) { _, _ ->
                val nom = champ.text.toString().trim()
                if (nom.isEmpty()) return@setPositiveButton
                val cible = File(courant, nom)
                if (cible.exists()) {
                    toast(getString(R.string.erreur_generique, "déjà présent"))
                    return@setPositiveButton
                }
                if (cible.mkdir()) {
                    toast(getString(R.string.dossier_cree))
                    rafraichir()
                } else {
                    toast(getString(R.string.erreur_generique, "création échouée"))
                }
            }
            .setNegativeButton(R.string.annuler, null)
            .show()
    }

    private fun coller() {
        val source = pressePapiers ?: run {
            toast(getString(R.string.rien_a_coller))
            return
        }
        val dansSoiMeme = courant.absolutePath == source.absolutePath ||
            (source.isDirectory && courant.absolutePath.startsWith(source.absolutePath + File.separator))
        if (dansSoiMeme) {
            toast(getString(R.string.impossible_coller_dans_soi_meme))
            return
        }
        if (couperMode && source.parentFile?.absolutePath == courant.absolutePath) {
            finaliserColler(R.string.deplacement_termine)
            return
        }
        val destination = nomUnique(courant, source.name)
        try {
            if (couperMode) {
                if (source.renameTo(destination)) {
                    finaliserColler(R.string.deplacement_termine)
                } else {
                    copierRecursif(source, destination)
                    if (source.deleteRecursively()) {
                        finaliserColler(R.string.deplacement_termine)
                    } else {
                        finaliserColler(R.string.copie_terminee)
                    }
                }
            } else {
                copierRecursif(source, destination)
                finaliserColler(R.string.copie_terminee)
            }
        } catch (e: Exception) {
            toast(getString(R.string.erreur_generique, e.message))
        }
    }

    private fun finaliserColler(messageRes: Int) {
        toast(getString(messageRes))
        pressePapiers = null
        couperMode = false
        majBoutonColler()
        rafraichir()
    }

    private fun copierRecursif(source: File, destination: File) {
        if (source.isDirectory) {
            if (!destination.exists()) destination.mkdirs()
            source.listFiles()?.forEach { enfant ->
                copierRecursif(enfant, File(destination, enfant.name))
            }
        } else {
            source.copyTo(destination, overwrite = false)
        }
    }

    private fun nomUnique(parent: File, nom: String): File {
        var candidat = File(parent, nom)
        if (!candidat.exists()) return candidat
        val base = candidat.nameWithoutExtension
        val extension = if (candidat.extension.isNotEmpty()) ".${candidat.extension}" else ""
        var i = 1
        while (true) {
            candidat = File(parent, "$base ($i)$extension")
            if (!candidat.exists()) return candidat
            i++
        }
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}
